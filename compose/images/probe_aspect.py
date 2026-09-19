"""2:3 / 3:2 在 2K、4K 档位能不能用？—— 实测探针。

背景：官方规格（ref_mask_test.py 注释里记录的）把比例和画质档绑死：
    low    -> 1024x1024 / 1536x1024 / 1024x1536   (1:1, 3:2, 2:3)
    medium -> 2048x2048 / 2048x1152 / 1152x2048   (1:1, 16:9, 9:16)
    high   -> 2880x2880 / 3840x2160 / 2160x3840   (1:1, 16:9, 9:16)
即 2:3 与 3:2 只出现在 low 档。但"规格没写"和"中转站会拒绝"是两件事，
而且 size_check.py 记录过一次 size 未被遵守（请求 1024x1024 得到 1254x1254），
所以必须实测三件事：
    1. HTTP 状态（400 = 直接拒绝）
    2. 响应里的 width/height 元数据
    3. 解码后图片的真实尺寸（是否被改写）

用法：
    python probe_aspect.py                # 只打印将要发送的内容，不发请求
    python probe_aspect.py --go           # 真的发送（每项 1 次请求，会消耗额度）
    python probe_aspect.py --go --only medium_2x3
"""
import argparse
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

# (名字, 画质档, 请求的 size, 说明)
CASES = [
    ("low_2x3_control", "low", "1024x1536",
     "对照：规格内的 2:3，1K。这项必须成功，否则说明探针本身有问题"),
    ("medium_1x1_control", "medium", "2048x2048",
     "对照：规格内的 1:1，2K。用来确认 medium 档本身可用"),
    ("medium_2x3", "medium", "1365x2048",
     "规格外的 2:3，2K（2048x2/3≈1365）"),
    ("medium_3x2", "medium", "2048x1365",
     "规格外的 3:2，2K"),
    ("high_2x3", "high", "2560x3840",
     "规格外的 2:3，4K（3840x2/3=2560）"),
    ("high_3x2", "high", "3840x2560",
     "规格外的 3:2，4K"),
]

PROMPT = "a plain flat grey-green background, no objects, no texture"


def make_input() -> bytes:
    """Small square input: keeps the upload cheap and works in every aspect."""
    im = Image.new("RGB", (512, 512), (180, 170, 160))
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def probe_one(eng: dict, base: str, key: str, quality: str, size: str,
              img: bytes) -> dict:
    bnd = ("----P" + uuid.uuid4().hex).encode()
    fields = {"model": eng["i2i_model"], "prompt": PROMPT, "n": "1",
              "size": size, "quality": quality}
    if not eng["edits_b64"]:
        fields["response_format"] = "b64_json"
    body = app.build_multipart(fields, {"image": ("image.png", img, "image/png")}, bnd)

    req = urllib.request.Request(base + "/images/edits", data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={bnd.decode()}")
    req.add_header("Authorization", "Bearer " + key)

    out = {"http": None, "error": "", "meta": {}, "actual": None}
    try:
        with urllib.request.urlopen(req, timeout=420,
                                    context=ssl.create_default_context()) as x:
            out["http"] = x.status
            data = json.loads(x.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        out["http"] = e.code
        out["error"] = e.read().decode("utf-8", "replace")[:400]
        return out
    except Exception as e:
        out["http"] = -1
        out["error"] = f"{type(e).__name__}: {e}"
        return out

    item = (data.get("data") or [{}])[0]
    out["meta"] = {k: item.get(k) for k in ("width", "height", "size_bytes", "mime_type")
                   if item.get(k) is not None}
    b64 = item.get("b64_json")
    if b64:
        raw = base64.b64decode(b64)
        out["actual"] = Image.open(io.BytesIO(raw)).size
    elif item.get("url"):
        out["error"] = "返回的是 url 而不是 b64（本机取不到该域名）"
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--go", action="store_true",
                    help="真的发送请求；不加这个参数只打印计划")
    ap.add_argument("--only", default="", help="只跑名字匹配的项（子串匹配）")
    ap.add_argument("--engine", default="gpt")
    a = ap.parse_args()

    eng = app.engine_of(a.engine)
    base = eng["base"]
    key = eng["key"]

    cases = [c for c in CASES if a.only in c[0]] if a.only else CASES
    if not cases:
        print(f"没有匹配 --only {a.only!r} 的项")
        return 1

    print(f"引擎: {a.engine}  模型: {eng['i2i_model']}")
    print(f"端点: {base}/images/edits")
    print(f"规格内的合法组合: " + "  ".join(
        f"{tier}={v}" for tier, v in eng["sizes"].items() if v))
    print()
    print("将要测试的项：")
    for name, quality, size, why in cases:
        w, h = (int(v) for v in size.split("x"))
        print(f"  {name:22} quality={quality:7} size={size:10} 比例={w / h:.3f}   {why}")
    print(f"\n共 {len(cases)} 次请求" + ("" if a.go else "（未发送）"))

    if not a.go:
        print("\n这是计划，没有发送任何请求。确认后加 --go 再跑。")
        return 0

    img = make_input()
    print("\n开始发送…\n")
    print(f"{'项':22}{'HTTP':>6}  {'请求':>11}  {'元数据':>11}  {'实际图片':>11}  判定")
    print("-" * 84)
    results = {}
    for name, quality, size, _why in cases:
        r = probe_one(eng, base, key, quality, size, img)
        meta = r["meta"]
        meta_s = (f"{meta.get('width')}x{meta.get('height')}"
                  if meta.get("width") else "-")
        actual_s = f"{r['actual'][0]}x{r['actual'][1]}" if r["actual"] else "-"
        if r["http"] == 200 and r["actual"]:
            ok = "尺寸被遵守" if actual_s == size else "**尺寸被改写**"
        elif r["http"] == 200:
            ok = "200 但没拿到图"
        else:
            ok = "拒绝"
        print(f"{name:22}{str(r['http']):>6}  {size:>11}  {meta_s:>11}  {actual_s:>11}  {ok}")
        if r["error"]:
            print(f"{'':22}└─ {r['error'].splitlines()[0][:100]}")
        results[name] = r

    print("\n" + "=" * 84)
    print("结论：")
    for name, quality, size, _why in cases:
        r = results[name]
        if r["http"] == 200 and r["actual"] and f"{r['actual'][0]}x{r['actual'][1]}" == size:
            verdict = f"可用 ✅ （{quality} 档真的按 {size} 出图）"
        elif r["http"] == 200:
            verdict = f"可用但尺寸被改写为 {r['actual']} ⚠️"
        else:
            verdict = f"不可用 ❌ HTTP {r['http']}"
        print(f"  {name:22} {verdict}")

    # 判定 2K / 4K 的 2:3、3:2 是否真的可行
    print()
    for tier, m2, m3 in (("medium", "medium_2x3", "medium_3x2"),
                         ("high", "high_2x3", "high_3x2")):
        good = [n for n in (m2, m3)
                if results.get(n, {}).get("http") == 200
                and results[n]["actual"]
                and f"{results[n]['actual'][0]}x{results[n]['actual'][1]}"
                == dict(CASES_BY_NAME)[n]]
        print(f"  {tier} 档的 2:3 / 3:2：{'可以配置 ✅' if good else '不能配置 ❌'}"
              + (f"（{', '.join(good)}）" if good else ""))
    return 0


CASES_BY_NAME = {c[0]: c[2] for c in CASES}

if __name__ == "__main__":
    raise SystemExit(main())
