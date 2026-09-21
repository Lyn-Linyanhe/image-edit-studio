"""gen.py 的健壮版包装：生成后把结果 URL 打出来，并对下载做重试。

gen.py 原版在 `urllib.request.urlopen(item["url"])` 处没有重试，对端偶发
RemoteDisconnected 就会把已经生成好的图丢掉（生成已经计费，白花一次）。
这里复用 gen.py 自己的 payload 构造，只把下载换成带退避的重试。

用法与 gen.py 一致：
  python gen2.py <image> <prompt-file|text> --style <ref> [--size 1024x1024]
                 [--quality low] [--pad crop] [--out out.png]
"""
from __future__ import annotations
import sys as _sys
# Windows 上 stdout 默认 cp936：打印 GBK 编不出的字符会直接崩，故脚本自带 UTF-8 前置。
# 这样不依赖 PYTHONIOENCODING 环境变量，也不会影响其它程序（见 SKILL.md 的「作业纪律」）。
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


import argparse
import base64
import io
import json
import os
import ssl
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "compose", "images"))
import gen as G  # noqa: E402
from PIL import Image  # noqa: E402


def fetch_with_retry(url: str, attempts: int = 6, timeout: int = 45) -> bytes:
    """短超时 + 多次重试，并且**优先用 curl**。

    两条实测教训：
    1) 曾用"300 秒超时 × 5 次"——下载一挂就把整条命令拖死（生成早就 HTTP 200 完成了）。
       下载超时必须明显短于生成耗时，改成 45 秒 × 6 次后第一次即成功。
    2) 这个 CDN（api.mikoto.vip）上 Python 的 urllib 会**连第一次尝试都不返回**，
       而 `curl.exe --max-time 60 --retry 3` 一次就取回（域名解析与 443 都正常，不换工具看不出来）。
       所以默认走 curl，失败再退回 urllib。
    """
    import shutil
    import subprocess
    import tempfile

    if shutil.which("curl.exe") or shutil.which("curl"):
        curl = shutil.which("curl.exe") or shutil.which("curl")
        for i in range(1, attempts + 1):
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
                tmp = tf.name
            r = subprocess.run(
                [curl, "-sS", "-L", "--max-time", str(timeout), "--retry", "2",
                 "--retry-delay", "3", "-A", "curl/8.0", "-o", tmp, url],
                capture_output=True, text=True,
            )
            if r.returncode == 0 and os.path.getsize(tmp) > 1024:
                data = open(tmp, "rb").read()
                os.unlink(tmp)
                return data
            print(f"   curl 第 {i}/{attempts} 次失败 rc={r.returncode} {r.stderr.strip()[:120]}", flush=True)
            time.sleep(min(2 * i, 10))
        print("   curl 全部失败，退回 urllib", flush=True)

    last = None
    for i in range(1, attempts + 1):
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8", "Accept": "image/png,*/*"})
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"   下载第 {i}/{attempts} 次失败: {type(e).__name__}: {e}", flush=True)
            time.sleep(min(2 * i, 10))
    raise SystemExit(f"   下载重试 {attempts} 次仍失败：{last}\n   URL 已打印，可手工下载")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("prompt")
    ap.add_argument("--style", default="")
    ap.add_argument("--size", default="1024x1024")
    ap.add_argument("--quality", default="low")
    ap.add_argument("--pad", default="crop", choices=["pad", "crop"])
    ap.add_argument("--model", default=G.MODEL)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    src = Image.open(a.image).convert("RGB")
    tw, th = (int(v) for v in a.size.split("x"))
    prompt = a.prompt
    if os.path.isfile(prompt):
        prompt = open(prompt, encoding="utf-8").read().strip()

    style_imgs = [Image.open(a.style).convert("RGB")] if a.style else []
    files, fit = G.build_whole(src, tw, th, a.pad, style=style_imgs)
    fields = {"model": a.model, "prompt": prompt, "n": "1", "size": a.size, "quality": a.quality}

    print(f"  source {a.image} {src.size} -> {a.size}  pad={a.pad}")
    total = sum(len(v[1]) for v in files.values())
    print(f"  sending {total} bytes ({total/1024/1024:.2f} MB)  files={list(files)}")

    t0 = time.time()
    st, txt = G.call(fields, files)
    print(f"  HTTP {st}   {time.time()-t0:.1f}s")
    if st != 200:
        print("FAILED:\n" + txt[:1200])
        return 1

    item = (json.loads(txt).get("data") or [{}])[0]
    raw = None
    if item.get("b64_json"):
        raw = base64.b64decode(item["b64_json"])
    elif item.get("url"):
        print(f"  result url: {item['url']}")
        raw = fetch_with_retry(item["url"])
    if not raw:
        print("no image in response: " + txt[:500])
        return 1

    Path(a.out).write_bytes(raw)
    print(f"  saved {a.out}  {Image.open(io.BytesIO(raw)).size}  {len(raw)//1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
