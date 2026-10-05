"""画廊收窄为"只从本轮起计入"：早于本轮的**不显示、也不计入**（去掉「全部历史」开关）。

用户口径（原话）："'只从最近这轮开始'是指'从这轮起才开始计入'，同时之前的全部隐藏即可"。

做法：
  · 扫描根由"整个 style-distill + compose"收窄为**只扫本轮目录**（style-distill/<最新的 round_*>）
  · 去掉范围开关（本轮/全部历史）与卡片上的 data-scope —— 之前的一律不出现
  · 页头写明：只显示本轮「X」，更早的轮次不计入、不显示
注意：分类器 gallery_category() 本身不动（它对旧文件仍能正确分类，将来每轮都复用同一套规则）。
"""
from __future__ import annotations

import pathlib
import py_compile
import sys

sys.stdout.reconfigure(encoding="utf-8")

P = pathlib.Path("compose/images/mask_edit_app.py")
t = P.read_text(encoding="utf-8")

pairs = [
    # 1) 扫描根收窄
    ('def _gallery_scan():\n'
     '    import os\n'
     '\n'
     '    found = []\n'
     '    for root in GALLERY_ROOTS:',
     'def scan_roots():\n'
     '    """只扫**本轮**目录（style-distill/<最新的 round_*>）。\n'
     '\n'
     '    口径来自用户："只从最近这轮开始，从这轮起才计入，之前的全部隐藏"。\n'
     '    自动识别本轮，所以开新一轮时画廊会自动跟过去，不需要改配置。\n'
     '    """\n'
     '    latest = latest_round()\n'
     '    if latest:\n'
     '        d = os.path.join(GALLERY_REL_BASE, "style-distill", latest)\n'
     '        if os.path.isdir(d):\n'
     '            return [d]\n'
     '    return list(GALLERY_ROOTS)          # 兜底：识别不到本轮时不至于空白\n'
     '\n'
     '\n'
     'def _gallery_scan():\n'
     '    """按修改时间倒序列出**本轮**目录里的图片（更早的轮次不计入、不显示）。"""\n'
     '    import os\n'
     '\n'
     '    found = []\n'
     '    for root in scan_roots():'),
    # 2) 去掉 scope 标签与统计
    ('        row["scope"] = "latest" if row["rel"].startswith(prefix) else "older"\n        kept.append(row)',
     '        kept.append(row)'),
    ('    latest = latest_round()\n'
     '    prefix = ("style-distill/" + latest + "/") if latest else "\\x00"\n'
     '    kept, process_seen = [], 0',
     '    latest = latest_round()\n'
     '    kept, process_seen = [], 0'),
    ('    counts["latest"] = sum(1 for r in kept if r["scope"] == "latest")\n'
     '    counts["older"] = len(kept) - counts["latest"]\n'
     '    counts["_latest_round"] = latest',
     '    counts["latest"] = len(kept)                 # 现在"计入的"就是"本轮的"\n'
     '    counts["older"] = 0                          # 更早的轮次不计入，也不显示\n'
     '    counts["_latest_round"] = latest'),
    # 3) 卡片去掉 data-scope
    ('        scope = row.get("scope", "older")\n        q = urllib.parse.quote(full)',
     '        q = urllib.parse.quote(full)'),
    ('            f\'<figure class="card" data-cat="{cat}" data-scope="{scope}">\'',
     '            f\'<figure class="card" data-cat="{cat}">\''),
    # 4) 去掉范围开关
    ("        f'<div class=\"tabs scope\">'\n"
     "        f'<button type=\"button\" class=\"tab on\" data-scope=\"latest\">本轮'\n"
     "        f'<span class=\"n\">{counts.get(\"latest\", 0)}</span></button>'\n"
     "        f'<button type=\"button\" class=\"tab\" data-scope=\"all\">全部历史'\n"
     "        f'<span class=\"n\">{counts.get(\"older\", 0)}</span></button>'\n"
     "        '</div>'\n",
     ""),
    # 5) JS 去掉 scope
    ("        'let cat=\"all\",scope=\"latest\",visible=[],at=0;'\n"
     "        'const scopeBtns=[...document.querySelectorAll(\".tabs.scope .tab\")];'",
     "        'let cat=\"all\",visible=[],at=0;'"),
    ("        'function apply(){const s=q.value.trim().toLowerCase();let total=0,shown=0;'\n"
     "        'for(const c of cards){const okScope=(scope===\"all\"||c.dataset.scope===scope);'\n"
     "        'const okCat=okScope&&(cat===\"all\"||c.dataset.cat===cat);'",
     "        'function apply(){const s=q.value.trim().toLowerCase();let total=0,shown=0;'\n"
     "        'for(const c of cards){const okCat=(cat===\"all\"||c.dataset.cat===cat);'"),
    ("        'for(const b of scopeBtns)b.classList.toggle(\"on\",b.dataset.scope===scope);'\n", ""),
    ("        'for(const b of scopeBtns)b.addEventListener(\"click\",()=>{scope=b.dataset.scope;apply();});'\n", ""),
    # 6) 页头说明
    ("        f'<span class=\"hint\" id=\"hint\">默认只看本轮「{counts.get(\"_latest_round\") or \"未识别\"}」'\n"
     "        f'（{counts.get(\"latest\", 0)} 张）；点「全部历史」看其余 {counts.get(\"older\", 0)} 张 · '\n"
     "        f'点图页内预览，←/→ 翻图'\n"
     "        f'{_input_note()}</span>'",
     "        f'<span class=\"hint\" id=\"hint\">只计入本轮「{counts.get(\"_latest_round\") or \"未识别\"}」'\n"
     "        f'（{counts.get(\"latest\", 0)} 张）；更早的轮次不计入、也不显示 · '\n"
     "        f'点图页内预览，←/→ 翻图'\n"
     "        f'{_input_note()}</span>'"),
]

for old, new in pairs:
    n = t.count(old)
    print(f"  锚点命中 {n} 次：{old.strip().splitlines()[0][:52] if old.strip() else '(空)'}")
    assert n == 1, f"锚点命中 {n} 次 → 停止"
    t = t.replace(old, new, 1)

P.write_text(t, encoding="utf-8")
py_compile.compile(str(P), doraise=True)
print("  已写入并编译通过")
