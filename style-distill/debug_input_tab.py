"""查：附件库里那 9 张"未进仓库的上传"为什么没被画廊列出来。"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("mea", ROOT / "compose/images/mask_edit_app.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

ui = m.user_inputs()
print(f"  索引读取：paths={len(ui['paths'])}  atts={len(ui['atts'])}")
print(f"  ATTACHMENTS_DIR = {m.ATTACHMENTS_DIR}")
print(f"  index 文件 = {m.USER_INPUT_INDEX}  存在={os.path.isfile(m.USER_INPUT_INDEX)}")

print("\n  逐条检查附件对象是否可 stat：")
for a in ui["atts"][:4]:
    oid = str(a.get("id"))
    p = os.path.join(m.ATTACHMENTS_DIR, "v1", "objects", oid[:2], oid[2:])
    print(f"     {oid[:16]}…  路径存在={os.path.isfile(p)}  {p}")

rows, counts = m.gallery_select()
att_rows = [r for r in rows if str(r["full"]).startswith("att:")]
print(f"\n  gallery_select 里 att: 行数 = {len(att_rows)}；输入计数 = {counts.get('input')}")
for r in att_rows[:4]:
    print(f"     {r['full'][:24]}…  {r['rel']}")
