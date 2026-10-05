"""生成"用户输入图"索引（带切点：只计入最近一次会话里的上传）。

用户的规则（原话）："之前的都不计入了，从刚才开始的那个开始计入"。
机械判据（可复现、不靠我猜）：
  会话日志里 role=user 的图片附件 → 每张记录它出现在哪些会话。
  · 只出现在**最近一次会话**里的上传 = "刚才开始的那些"（本次正是街机轮的图1/图2 两张）
  · 出现在更早会话（被后续会话继承历史）里的 = "之前的"，不计入
产出 style-distill/round_lib/user_inputs.json：
  cutoff_session  切点会话名
  paths           计入的上传在工作区里的文件
  excluded        被排除的上传（名字/尺寸/字节，供页面如实标注）
  unreachable     被排除且只在附件库、无法在画廊定位的那些
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
SESS = Path(os.path.expanduser("~")) / ".dsh" / "sessions" / "--C-Users-typ-Desktop-mantu--"
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

# 最近一次会话（按 mtime）
sessions = sorted((p for p in SESS.glob("*/session.jsonl.zstd")), key=lambda p: p.stat().st_mtime)
newest_full = sessions[-1].parent.name if sessions else ""
newest = newest_full[:20]          # ⚠ 提取脚本里会话名按 20 字符截断存过（session-05d8fe01-e83），两边要一致
print(f"  最近一次会话：{newest_full}（比对用 {newest}）")

counted, excluded = {}, {}
for h, meta in uploads.items():
    (counted if set(meta["sessions"]) == {newest} else excluded)[h] = meta
print(f"  计入 {len(counted)} 张（只属于最近会话）；排除 {len(excluded)} 张（更早会话/被继承）")

by_hash = {h: m["att"] for h, m in counted.items()}
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

paths = sorted({x for v in ws.values() for x in v})
excl_list = [{"name": m["att"].get("name", "?"), "width": m["att"].get("width"),
              "height": m["att"].get("height"), "bytes": m["att"].get("bytes")}
             for m in excluded.values()]
# 被排除且工作区里找不到同源文件的 → 只在附件库（无法在画廊定位）
ws_all = set()
for root in (BASE / "style-distill", BASE / "compose"):
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in ("node_modules", "__pycache__", ".git")]
        ws_all.update((Path(dp) / f).as_posix() for f in fn)
unreachable = []
for h, m in excluded.items():
    hit = False
    for root in (BASE / "style-distill", BASE / "compose"):
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in ("node_modules", "__pycache__", ".git")]
            for f in fn:
                p = Path(dp) / f
                if p.suffix.lower() not in EXTS:
                    continue
                try:
                    if sha(p) == h:
                        hit = True
                        break
                except OSError:
                    continue
            if hit:
                break
        if hit:
            break
    if not hit:
        unreachable.append(m["att"].get("name", "?"))

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({
    "cutoff_session": newest,
    "paths": paths,
    "excluded": excl_list,
    "unreachable": unreachable,
}, ensure_ascii=False, indent=1), encoding="utf-8")

print(f"\n  计入的上传 → 工作区文件 {len(paths)} 个：")
for p in paths:
    print(f"     {p}")
print(f"  排除的上传 {len(excl_list)} 张（其中 {len(unreachable)} 张只在附件库）")
print(f"  已写出 {OUT.relative_to(BASE)}")
