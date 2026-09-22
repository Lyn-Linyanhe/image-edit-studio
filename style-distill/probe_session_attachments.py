"""从会话日志里提取"用户上传的图片"（权威来源，不靠命名约定）。

日志：~/.dsh/sessions/--C-Users-typ-Desktop-mantu--/*/session.jsonl.zstd
Python 3.14 自带 compression.zstd。先看结构：记录里有 role、附件标注（sha256 / objects 路径）。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

try:
    from compression import zstd                     # Python 3.14+
except Exception as e:                               # noqa: BLE001
    print(f"  没有内置 zstd：{e}")
    raise SystemExit(1)

SESS = Path(os.path.expanduser("~")) / ".dsh" / "sessions" / "--C-Users-typ-Desktop-mantu--"
files = sorted(SESS.glob("*/session.jsonl.zstd"), key=lambda p: p.stat().st_mtime, reverse=True)
print(f"  mantu 会话 {len(files)} 个；最大的是 {files[0].name}（{files[0].stat().st_size//1024} KB）\n")

p = files[0]
raw = zstd.decompress(p.read_bytes())
lines = raw.decode("utf-8", "replace").splitlines()
print(f"  解压 {p.parent.name}：{len(raw)} 字节 / {len(lines)} 行")

roles = {}
for ln in lines:
    try:
        rec = json.loads(ln)
    except Exception:
        continue
    role = rec.get("role") or (rec.get("message") or {}).get("role") or "?"
    roles[role] = roles.get(role, 0) + 1
print(f"  记录 role 分布：{roles}")

print("\n  前 3 条记录的顶层键（看结构）：")
shown = 0
for ln in lines:
    try:
        rec = json.loads(ln)
    except Exception:
        continue
    print(f"    keys={list(rec)[:10]}")
    shown += 1
    if shown >= 3:
        break

print("\n  含 'sha256:' 的行数与样例：")
hit = [ln for ln in lines if "sha256:" in ln]
print(f"    命中 {len(hit)} 行")
for ln in hit[:3]:
    i = ln.find("sha256:")
    print("    …" + ln[max(0, i - 90):i + 80].replace("\\n", " ") + "…")

print("\n  含 'objects/' 的行数：", sum(1 for ln in lines if "objects/" in ln))
