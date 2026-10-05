"""把"用户上传过的 21 张"与工作区文件配对，产出「参考（你的输入）」的准确清单。

输入：_probe/user_attachments.json（上一步从会话日志提取）
输出：每个上传对象 → 原始文件名/尺寸/字节 → 工作区里的副本（若有）
"""
from __future__ import annotations
import os as _os
_MANTU_ROOT_STR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *([".."] * 1)))

import hashlib
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(_MANTU_ROOT_STR)
ATT = Path(os.path.expanduser("~")) / ".dsh" / "attachments"
EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

data = json.loads((Path(__file__).resolve().parent / "_probe" / "user_attachments.json")
                  .read_text(encoding="utf-8"))


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


print(f"  用户上传对象 {len(data)} 个；逐个配对工作区文件：\n")
in_ws_total = 0
rows = []
for h, meta in sorted(data.items()):
    att = meta["att"]
    name = att.get("name", "?")
    wh = f"{att.get('width')}x{att.get('height')}"
    nbytes = att.get("bytes")
    hits = []
    for root in (BASE / "style-distill", BASE / "compose"):
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in ("node_modules", "__pycache__", ".git")]
            for f in fn:
                p = Path(dp) / f
                if p.suffix.lower() not in EXTS:
                    continue
                try:
                    if sha(p) == h:
                        hits.append(p.relative_to(BASE))
                except OSError:
                    continue
    in_ws_total += 1 if hits else 0
    rows.append((name, wh, nbytes, hits))
    tag = "在工作区" if hits else "仅在上传目录"
    print(f"  [{tag}] {name:42s} {wh:>10s} {str(nbytes):>9s} B")
    for x in hits:
        print(f"        → {x}")

print(f"\n  21 张里有 {in_ws_total} 张被复制进了工作区，"
      f"{len(data) - in_ws_total} 张只在附件库里。")
