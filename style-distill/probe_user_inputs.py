"""找出"用户自己输入的图片"——不猜命名，用哈希配对。

依据：用户上传的图会落在附件库 ~/.dsh/attachments/v1/objects/**；
我当时是直接从那里 Copy-Item 到各轮 input/ 的，所以工作区副本与附件对象**字节一致**。
本脚本：① 列出附件库里的图片对象；② 与工作区图片做哈希配对；
        ③ 顺带标出"由用户图派生的"（尺寸/内容相关但哈希不同，例如我裁的 C_/D_ 版本）。
"""
from __future__ import annotations

import hashlib
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = r"C:\Users\typ\Desktop\mantu"
ATT = os.path.join(os.path.expanduser("~"), ".dsh", "attachments")
ROOTS = [os.path.join(BASE, "style-distill"), os.path.join(BASE, "compose")]
EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def sha(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def walk_images(root: str):
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in ("node_modules", "__pycache__", ".git")]
        for f in fn:
            p = os.path.join(dp, f)
            if os.path.splitext(f)[1].lower() in EXTS:
                yield p


print("  ① 附件库（用户上传）对象：")
att = {}
for dp, dn, fn in os.walk(ATT):          # ⚠ 附件对象没有扩展名（内容寻址），不按后缀筛
    for f in fn:
        p = os.path.join(dp, f)
        try:
            s = sha(p)
        except OSError:
            continue
        att.setdefault(s, []).append(p)
for s, ps in att.items():
    rel = [os.path.relpath(x, ATT) for x in ps]
    size = os.path.getsize(ps[0])
    print(f"     {s[:16]}  {size:>9d} B  {rel}")

print(f"     → 附件库图片对象共 {len(att)} 个（去重后）")

print("\n  ② 工作区里哪些图与附件对象字节一致（＝用户输入的图）：")
matched, unmatched = [], []
for p in walk_images(BASE):
    try:
        s = sha(p)
    except OSError:
        continue
    if s in att:
        matched.append((p, s))
    else:
        unmatched.append(p)

for p, s in sorted(matched):
    print(f"     ✓ {s[:16]}  {os.path.relpath(p, BASE)}")
print(f"     → 命中 {len(matched)} 张；工作区图片总数 {len(matched) + len(unmatched)}")

print("\n  ③ 附件库里还没进工作区的（只在上传目录里的）：")
in_ws = {sha(p) for p, _ in matched}
for s, ps in att.items():
    if s not in in_ws:
        for x in ps:
            print(f"     · {s[:16]}  {os.path.getsize(x):>9d} B  {os.path.relpath(x, ATT)}")
