"""提取"用户上传过的图片"清单（跨所有 mantu 会话），并落到 workspace 的对应文件。

判据：会话记录里 role=user 的消息内容中的 `{"type":"image","attachment":{"attachmentId":"sha256:…"}}`。
工具结果里的图片（我 read_image 的）role 不是 user，天然被排除。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
from compression import zstd                                    # noqa: E402

SESS = Path(os.path.expanduser("~")) / ".dsh" / "sessions" / "--C-Users-typ-Desktop-mantu--"
files = sorted(SESS.glob("*/session.jsonl.zstd"), key=lambda p: p.stat().st_mtime)


def walk(o, out, seen_dbg):
    if isinstance(o, dict):
        if o.get("role") and isinstance(o.get("content"), list):
            for item in o["content"]:
                if isinstance(item, dict) and item.get("type") == "image":
                    att = item.get("attachment") or {}
                    aid = str(att.get("attachmentId") or "")
                    if aid.startswith("sha256:"):
                        out.append((o.get("role"), aid[7:], att))
                        if not seen_dbg:
                            seen_dbg.append(att)
        for v in o.values():
            walk(v, out, seen_dbg)
    elif isinstance(o, list):
        for v in o:
            walk(v, out, seen_dbg)


all_user: dict[str, dict] = {}
dbg: list = []
for p in files:
    try:
        raw = zstd.decompress(p.read_bytes())
    except Exception as e:                                       # noqa: BLE001
        print(f"  跳过 {p.parent.name}：{e}")
        continue
    found: list = []
    for ln in raw.decode("utf-8", "replace").splitlines():
        try:
            walk(json.loads(ln), found, dbg)
        except Exception:
            continue
    n_user = 0
    for role, h, att in found:
        if role != "user":
            continue
        n_user += 1
        all_user.setdefault(h, {"sessions": set(), "att": att})
        all_user[h]["sessions"].add(p.parent.name[:20])
    print(f"  {p.parent.name[:20]}  用户附图 {n_user} 张（含重复）")

print(f"\n  去重后用户上传过 {len(all_user)} 张")
print("\n  附件元数据的字段（取一条看）：")
if dbg:
    print("   ", json.dumps(dbg[0], ensure_ascii=False)[:400])

# 落到文件
out_path = Path(__file__).resolve().parent / "_probe" / "user_attachments.json"
out_path.parent.mkdir(exist_ok=True)
out_path.write_text(json.dumps(
    {h: {"sessions": sorted(v["sessions"]), "att": {k: str(val) for k, val in v["att"].items()}}
     for h, v in all_user.items()}, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\n  已落盘：{out_path}")
