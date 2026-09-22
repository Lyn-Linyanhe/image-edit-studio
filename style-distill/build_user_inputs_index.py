"""生成"用户输入图"索引：style-distill/round_lib/user_inputs.json

来源两条（都是证据，不是命名约定）：
  ① 会话日志里 role=user 消息的 image 附件（extract_user_attachments.py 已提取到 _probe/）
  ② 与工作区图片做 sha256 配对
产出：
  paths       —— 工作区里属于"用户输入"的文件（相对仓库根的 POSIX 路径）
  attachments —— 只存在于附件库、尚未复制进工作区的上传（供画廊直接展示）
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(r"C:\Users\typ\Desktop\mantu")
ATT = Path(os.path.expanduser("~")) / ".dsh" / "attachments"
EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
PROBE = Path(__file__).resolve().parent / "_probe" / "user_attachments.json"
OUT = BASE / "style-distill" / "round_lib" / "user_inputs.json"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


uploads = json.loads(PROBE.read_text(encoding="utf-8"))
by_hash = {h: m["att"] for h, m in uploads.items()}

ws: dict[str, list[str]] = {}
for root in (BASE / "style-distill", BASE / "compose"):
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in ("node_modules", "__pycache__", ".git")]
        for f in fn:
            p = Path(dp) / f
            if p.suffix.lower() not in EXTS:
                continue
            try:
                h = sha(p)
            except OSError:
                continue
            if h in by_hash:
                ws.setdefault(h, []).append(p.relative_to(BASE).as_posix())

paths: list[str] = sorted({x for v in ws.values() for x in v})
att_only = [{"id": h, "name": a.get("name", "?"), "mediaType": a.get("mediaType", ""),
             "width": a.get("width"), "height": a.get("height"), "bytes": a.get("bytes")}
            for h, a in sorted(by_hash.items()) if h not in ws]

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"paths": paths, "attachments": att_only},
                          ensure_ascii=False, indent=1), encoding="utf-8")

print(f"  用户上传 {len(uploads)} 张 → 工作区内有 {len(paths)} 个文件，"
      f"仅附件库 {len(att_only)} 张")
print(f"  已写出 {OUT.relative_to(BASE)}")
for p in paths:
    print(f"     {p}")
print("  仅附件库的：")
for a in att_only:
    print(f"     {a['name']:44s} {a['width']}x{a['height']} {a['bytes']} B")
