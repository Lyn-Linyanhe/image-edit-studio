"""看每张上传出现在哪些会话——用来确定"从刚才那一张开始计入"的准确切点。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
d = json.loads((Path(__file__).resolve().parent / "_probe" / "user_attachments.json")
               .read_text(encoding="utf-8"))
rows = sorted(d.items(), key=lambda kv: (sorted(kv[1]["sessions"])[0], kv[1]["att"].get("name", "")))
for h, v in rows:
    a = v["att"]
    print(f"  {h[:12]}  {a.get('name','?'):44s} {a.get('width')}x{a.get('height')}"
          f"  {str(a.get('bytes')):>9s} B  {v['sessions']}")
print(f"\n  合计 {len(rows)} 张")
