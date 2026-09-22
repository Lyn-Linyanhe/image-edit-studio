"""核实两件事：
  ① round_snow/input/C_snow.jpg 与 round_manga/input/c1dc05a…720.jpg 是不是同一张（哈希比对）
  ② 若加"内容"页签，按"README 的 input/ 定义"会装进哪些文件（逐条列出）
"""
from __future__ import annotations

import hashlib
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
BASE = r"C:\Users\typ\Desktop\mantu"

a = os.path.join(BASE, r"style-distill\round_snow\input\C_snow.jpg")
b = os.path.join(BASE, r"style-distill\round_manga\input\c1dc05a287896769311f364517a30509_720.jpg")


def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


print("  ① 哈希比对")
for p in (a, b):
    print(f"     {sha(p)[:16]}  {os.path.getsize(p):>8d} B  {os.path.relpath(p, BASE)}")
print(f"     → {'**同一张图**' if sha(a) == sha(b) else '不是同一张'}")

print("\n  ② 若加'内容'页签，候选（各轮 input/ 下的图，按 README 的'输入图'定义）：")
for root in ("style-distill/round_arcade", "style-distill/round_manga",
             "style-distill/round_snow", "style-distill/round_lib"):
    d = os.path.join(BASE, root.replace("/", os.sep), "input")
    if not os.path.isdir(d):
        continue
    print(f"     {root}/input/")
    for f in sorted(os.listdir(d)):
        p = os.path.join(d, f)
        if os.path.isfile(p) and os.path.splitext(f)[1].lower() in {".png", ".jpg", ".jpeg"}:
            print(f"        {f:44s} {os.path.getsize(p):>9d} B")

print("\n  另：旧轮 target_t2/ 里与'目标图'同族的：")
d2 = os.path.join(BASE, r"style-distill\target_t2")
for f in ("input.png", "clean.png", "clean_v2.png", "zoom.png", "grid.png", "mask.png", "mask_vis.png"):
    p = os.path.join(d2, f)
    if os.path.isfile(p):
        print(f"     {f:16s} {os.path.getsize(p):>9d} B")
