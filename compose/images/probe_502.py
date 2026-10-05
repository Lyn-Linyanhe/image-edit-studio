"""定位 502 "Upstream access forbidden" 的成因：逐项隔离变量，命中失败即停。

背景：一次真实请求失败，诊断为
    HTTP 502 {"error":{"message":"Upstream access forbidden, please contact administrator",
                       "type":"upstream_error"}}
    画质=medium  尺寸=2048x2048  参考图=2 张  模式=整张图
502 是中转站上游给的，不是我们的请求格式问题（那会是 400），所以必须分开测。

按"最便宜且信息量最大"的顺序，任一步失败就停下并报告：
    0. GET /models                 免费，测 key / 中转站是否可用
    1. 1 张图 · low · 1024x1536    最省的基线：图生图到底能不能用
    2. 1 张图 · medium · 2048x2048 只变画质+尺寸，测 medium 档
    3. 1 张图 + 2 参考图 · low     只变参考图，测多图（用 low 省钱）
    4. 1 张图 + 2 参考图 · medium  复现你那次失败的完整组合

用法：
    python probe_502.py            # 只打印计划
    python probe_502.py --go       # 真跑（最多 4 次生成，命中失败即停）
    python probe_502.py --go --through 1     # 只跑到第 1 步
"""
import argparse
import os as _os
_MANTU_ROOT_STR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *([".."] * 2)))
import base64
import io
import json
import ssl
import sys
import urllib.error
import urllib.request
import uuid

sys.path.insert(0, ".")
import mask_edit_app as app  # noqa: E402
from PIL import Image  # noqa: E402

TARGET = rf"{_MANTU_ROOT_STR}\style-distill\target\target.png"
REF2 = rf"{_MANTU_ROOT_STR}\47EC32AC427193D005E9658AF8461F97.jpg"
REF3 = rf"{_MANTU_ROOT_STR}\187DAFA40C9A79628386C5EE4F6966C4.jpg"

SHORT_PROMPT = "smooth flat grey-green background, no objects"


def load(p, max_edge=1024):
    im = Image.open(p).convert("RGB")
    s = min(1.0, max_edge / max(im.size))
    if s < 1.0:
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, "PNG", optimize=True)
    return b.getvalue()


def post_edits(base, key, model, prompt, size, quality, images):
    """images: list of bytes; the first goes on `image`, the rest on image[1..]"""
    bnd = ("----X" + uuid.uuid4().hex).encode()
    fields = {"model": model, "prompt": prompt, "n": "1", "size": size, "quality": quality}
    files = {"image": ("image.png", images[0], "image/png")}
    for i, b in enumerate(images[1:], start=1):
        files[f"image[{i}]"] = (f"ref{i}.png", b, "image/png")
    body = app.build_multipart(fields, files, bnd)
    req = urllib.request.Request(base + "/images/edits", data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={bnd.decode()}")
    req.add_header("Authorization", "Bearer " + key)
    try:
        with urllib.request.urlopen(req, timeout=420,
                                    context=ssl.create_default_context()) as x:
            data = json.loads(x.read().decode("utf-8", "replace"))
        it = (data.get("data") or [{}])[0]
        out = {"http": x.status, "err": ""}
        if it.get("b64_json"):
            out["actual"] = Image.open(io.BytesIO(base64.b64decode(it["b64_json"]))).size
        else:
            out["err"] = "200 但没有 b64（可能返回了 url）"
        return out
    except urllib.error.HTTPError as e:
        return {"http": e.code, "err": e.read().decode("utf-8", "replace")[:300]}
    except Exception as e:
        return {"http": -1, "err": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--go", action="store_true", help="真的发送；不加只打印计划")
    ap.add_argument("--through", type=int, default=99, help="只跑到第 N 步")
    a = ap.parse_args()

    eng = app.engine_of("gpt")
    base, key, model = eng["base"], eng["key"], eng["i2i_model"]

    plan = [
        (0, "GET /models（免费）", None),
        (1, "1 图 · low · 1024x1536", ("low", "1024x1536", 1)),
        (2, "1 图 · medium · 2048x2048（只变画质/尺寸）", ("medium", "2048x2048", 1)),
        (3, "1 图 + 2 参考图 · low · 1024x1536（只变参考图）", ("low", "1024x1536", 3)),
        (4, "1 图 + 2 参考图 · medium · 2048x2048（复现失败组合）", ("medium", "2048x2048", 3)),
    ]
    print(f"端点: {base}")
    print(f"模型: {model}\n")
    for n, label, _ in plan:
        print(f"  步骤 {n}: {label}")
    if not a.go:
        print("\n这是计划，未发送任何请求。确认后加 --go。")
        return 0

    target = load(TARGET)
    refs = [load(REF2), load(REF3)]
    print(f"\n图1 输入 {len(target)//1024} KB；两张参考各 {len(refs[0])//1024} KB / {len(refs[1])//1024} KB\n")
    print(f"{'步骤':6}{'说明':44}{'HTTP':>6}  {'结果':10}")
    print("-" * 80)

    for n, label, cfg in plan:
        if n > a.through:
            break
        if n == 0:
            req = urllib.request.Request(base + "/models")
            req.add_header("Authorization", f"Bearer {key}")
            try:
                with urllib.request.urlopen(req, timeout=30,
                                            context=ssl.create_default_context()) as x:
                    d = json.loads(x.read().decode("utf-8", "replace"))
                cnt = len(d.get("data") or [])
                print(f"{n:<6}{label:44}{x.status:>6}  可用模型 {cnt} 个")
                continue
            except urllib.error.HTTPError as e:
                print(f"{n:<6}{label:44}{e.code:>6}  {e.read().decode('utf-8','replace')[:60]}")
                print("\n→ /models 就失败了：key 或中转站本身有问题，后面的生成步骤无意义。")
                return 1
            except Exception as e:
                print(f"{n:<6}{label:44}{'ERR':>6}  {type(e).__name__}: {e}")
                return 1

        quality, size, count = cfg
        imgs = [target] + (refs if count == 3 else [])
        r = post_edits(base, key, model, SHORT_PROMPT, size, quality, imgs)
        verdict = "OK " + str(r.get("actual", "")) if r["http"] == 200 and not r["err"] else "失败"
        print(f"{n:<6}{label:44}{str(r['http']):>6}  {verdict}")
        if r["err"]:
            print(f"{'':6}└─ {r['err'].splitlines()[0][:110]}")
        if r["http"] != 200 or r["err"]:
            print(f"\n→ 在第 {n} 步复现失败，前一步是成功的。问题就出在步骤 {n} 引入的那个变量上。")
            return 1

    print("\n→ 全部步骤都成功：说明链路本身可用，你那次 502 更可能是中转站上游的临时故障，重试即可。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
