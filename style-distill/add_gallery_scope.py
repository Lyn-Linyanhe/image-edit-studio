"""画廊加"范围"开关：默认只显示**最近的这一轮**，历史收起来（可一键切到全部）。

用户要求："现在的这些都隐藏吧，只从最近的这轮开始"。
做法：每个卡片带 data-scope（latest / older），页头加两个范围按钮，默认 latest。
  本轮 = style-distill 下按 mtime 最新的 round_* 目录（排除 round_lib）。
"""
from __future__ import annotations

import pathlib
import py_compile
import sys

sys.stdout.reconfigure(encoding="utf-8")

P = pathlib.Path("compose/images/mask_edit_app.py")
t = P.read_text(encoding="utf-8")

pairs = [
    # 1) 找本轮 + 打 scope 标签 + 统计
    ('def gallery_select():\n'
     '    """成果与局部全取；过程只取最新 GALLERY_PROCESS_CAP 张。\n'
     '\n'
     '    另外把"只存在附件库、未复制进工作区"的用户上传也作为条目列出来\n'
     '    （full = "att:<sha256>"，由 /gallery/img 直接从附件库服务）。\n'
     '    """\n'
     '    rows = _gallery_scan()\n'
     '    kept, process_seen = [], 0\n'
     '    for row in rows:\n'
     '        if row["cat"] == "process":\n'
     '            process_seen += 1\n'
     '            if process_seen > GALLERY_PROCESS_CAP:\n'
     '                continue\n'
     '        kept.append(row)\n'
     '    # 注意：按切点排除掉的上传**不再**合成行——它们要么是"之前的"，要么无法在画廊定位。\n'
     '    counts = {key: 0 for key, _ in CATEGORIES}\n'
     '    counts["all"] = len(kept)\n'
     '    for row in kept:\n'
     '        counts[row["cat"]] = counts.get(row["cat"], 0) + 1\n'
     '    return kept, counts',
     'def latest_round() -> str:\n'
     '    """最近的这一轮：style-distill 下按 mtime 最新的 round_* 目录（排除 round_lib）。"""\n'
     '    import glob\n'
     '\n'
     '    best, best_m = "", -1.0\n'
     '    for d in glob.glob(os.path.join(GALLERY_REL_BASE, "style-distill", "round_*")):\n'
     '        base = os.path.basename(d)\n'
     '        if base in ROUND_ROOT_DENY or not os.path.isdir(d):\n'
     '            continue\n'
     '        try:\n'
     '            m = os.stat(d).st_mtime\n'
     '        except OSError:\n'
     '            continue\n'
     '        if m > best_m:\n'
     '            best, best_m = base, m\n'
     '    return best\n'
     '\n'
     '\n'
     'def gallery_select():\n'
     '    """成果与局部全取；过程只取最新 GALLERY_PROCESS_CAP 张。\n'
     '\n'
     '    每行带 scope：属于**最近这一轮**的为 latest，其余 older（页面默认只显示 latest）。\n'
     '    """\n'
     '    rows = _gallery_scan()\n'
     '    latest = latest_round()\n'
     '    prefix = ("style-distill/" + latest + "/") if latest else "\\x00"\n'
     '    kept, process_seen = [], 0\n'
     '    for row in rows:\n'
     '        if row["cat"] == "process":\n'
     '            process_seen += 1\n'
     '            if process_seen > GALLERY_PROCESS_CAP:\n'
     '                continue\n'
     '        row["scope"] = "latest" if row["rel"].startswith(prefix) else "older"\n'
     '        kept.append(row)\n'
     '    counts = {key: 0 for key, _ in CATEGORIES}\n'
     '    counts["all"] = len(kept)\n'
     '    for row in kept:\n'
     '        counts[row["cat"]] = counts.get(row["cat"], 0) + 1\n'
     '    counts["latest"] = sum(1 for r in kept if r["scope"] == "latest")\n'
     '    counts["older"] = len(kept) - counts["latest"]\n'
     '    counts["_latest_round"] = latest\n'
     '    return kept, counts'),
    # 2) 卡片带 scope
    ("        cat = row[\"cat\"]\n        q = urllib.parse.quote(full)\n"
     "        cards.append(\n"
     "            f'<figure class=\"card\" data-cat=\"{cat}\">'",
     "        cat = row[\"cat\"]\n"
     "        scope = row.get(\"scope\", \"older\")\n"
     "        q = urllib.parse.quote(full)\n"
     "        cards.append(\n"
     "            f'<figure class=\"card\" data-cat=\"{cat}\" data-scope=\"{scope}\">'"),
    # 3) 范围按钮 + 页头计数
    ("        '<header><h1>图片</h1>'\n"
     "        f'<div class=\"tabs\">{tabs}</div>'",
     "        '<header><h1>图片</h1>'\n"
     "        f'<div class=\"tabs scope\">'\n"
     "        f'<button type=\"button\" class=\"tab on\" data-scope=\"latest\">本轮'\n"
     "        f'<span class=\"n\">{counts.get(\"latest\", 0)}</span></button>'\n"
     "        f'<button type=\"button\" class=\"tab\" data-scope=\"all\">全部历史'\n"
     "        f'<span class=\"n\">{counts.get(\"older\", 0)}</span></button>'\n"
     "        '</div>'\n"
     "        f'<div class=\"tabs\">{tabs}</div>'"),
    # 4) JS：加 scope 状态
    ("        'let cat=\"all\",visible=[],at=0;'",
     "        'let cat=\"all\",scope=\"latest\",visible=[],at=0;'\n"
     "        'const scopeBtns=[...document.querySelectorAll(\".tabs.scope .tab\")];'"),
    ("        'function apply(){const s=q.value.trim().toLowerCase();let total=0,shown=0;'\n"
     "        'for(const c of cards){const okCat=(cat===\"all\"||c.dataset.cat===cat);'",
     "        'function apply(){const s=q.value.trim().toLowerCase();let total=0,shown=0;'\n"
     "        'for(const c of cards){const okScope=(scope===\"all\"||c.dataset.scope===scope);'\n"
     "        'const okCat=okScope&&(cat===\"all\"||c.dataset.cat===cat);'"),
    ("        'for(const t of tabs)t.classList.toggle(\"on\",t.dataset.cat===cat);'",
     "        'for(const t of tabs)t.classList.toggle(\"on\",t.dataset.cat===cat);'\n"
     "        'for(const b of scopeBtns)b.classList.toggle(\"on\",b.dataset.scope===scope);'"),
    ("        'for(const t of tabs)t.addEventListener(\"click\",()=>{cat=t.dataset.cat;apply();});'",
     "        'for(const t of tabs)t.addEventListener(\"click\",()=>{cat=t.dataset.cat;apply();});'\n"
     "        'for(const b of scopeBtns)b.addEventListener(\"click\",()=>{scope=b.dataset.scope;apply();});'"),
    # 5) 页头说明
    ("        f'<span class=\"hint\" id=\"hint\">共 {counts[\"all\"]} 张；'\n"
     "        f'成果与局部一张不落，过程只取最新 {GALLERY_PROCESS_CAP} 张 · 点图页内预览，←/→ 翻图'\n"
     "        f'{_input_note()}</span>'",
     "        f'<span class=\"hint\" id=\"hint\">默认只看**本轮 {counts.get(\"_latest_round\") or \"（未识别）\"}**'\n"
     "        f'（{counts.get(\"latest\", 0)} 张）；点「全部历史」看其余 {counts.get(\"older\", 0)} 张 · '\n"
     "        f'点图页内预览，←/→ 翻图'\n"
     "        f'{_input_note()}</span>'"),
]

for old, new in pairs:
    n = t.count(old)
    print(f"  锚点命中 {n} 次：{old.strip().splitlines()[0][:50]}")
    assert n == 1, f"锚点命中 {n} 次 → 停止"
    t = t.replace(old, new)

P.write_text(t, encoding="utf-8")
py_compile.compile(str(P), doraise=True)
print("  已写入并编译通过")
