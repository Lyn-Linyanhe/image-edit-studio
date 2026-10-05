#!/usr/bin/env python3
"""补下结果图：用 run_round 的新下载策略（探测式抢高速档）。

两种用法：
  python fetch_url.py <url> <输出路径>          # 直接下一条
  python fetch_url.py --pending                 # 把 pending_urls.json 里所有未完成的补齐

为什么单独有这个脚本：生成一返回 URL 就记进 `run_round.py` 旁边的 `pending_urls.json`，
下载慢或失败时（本次 4K 就是）URL 不会丢，事后可以直接补下，不必翻终端日志。
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
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import run_round as R  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--pending", action="store_true")
    a = ap.parse_args()

    if a.pending:
        if not R.PENDING.exists():
            print("没有 pending_urls.json")
            return 1
        items = json.loads(R.PENDING.read_text(encoding="utf-8"))
        todo = [d for d in items if d.get("status") != "done"]
        print(f"待补下 {len(todo)} 条 / 共 {len(items)} 条")
        for d in todo:
            out = Path(d["out"])
            print(f"=== {out.name}", flush=True)
            try:
                R.download(d["url"], out)
                R.note_pending(out, d["url"], "done")
                print("   已标记 done", flush=True)
            except SystemExit as e:
                print(f"   仍失败：{e}", flush=True)
        return 0

    if not a.url or not a.out:
        raise SystemExit("需要 <url> <输出路径>，或用 --pending")
    out = Path(a.out)
    R.download(a.url, out)
    R.note_pending(out, a.url, "done")
    from PIL import Image
    im = Image.open(out)
    print(f"完成：{out}  {im.size}  {out.stat().st_size/1048576:.2f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
