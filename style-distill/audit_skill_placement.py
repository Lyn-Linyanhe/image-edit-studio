"""审查取证：把"规则该在主流程、实际却滞留在账本"这件事用计数证明。

输出三张表：
  表1 规则落位审查——每条规则在 LESSONS.md（账本）与 SKILL.md＋template.md＋pipeline-notes.md（主流程）里的命中次数
  表2 生成时间线——从 pending_urls.json 的时间戳看实际节奏
  表3 下载速率实测汇总——本次所有实测点
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SK = Path.home() / ".agents" / "skills" / "style-distill"
LESSONS = SK / "LESSONS.md"
MAIN = [SK / "SKILL.md", SK / "references" / "template.md", SK / "references" / "pipeline-notes.md"]

RULES = {
    "①确定性优先（改这一张 vs 这一类）": ["确定性", "改这一张", "本地像素处理", "不调接口"],
    "②体积预算预检": ["体积预算", "1.96", "4.36", "MiB 通过", "画幅"],
    "③取回结果是独立步骤": ["探测式", "speed-limit", "pending_urls", "解码校验", "截断", "取回"],
    "④验证脚本化（别靠肉眼）": ["脚本化", "tone_report", "肉眼", "body_report"],
    "⑤中间稿一律 1K": ["中间稿", "一律 1K", "只在最终交付"],
    "⑥多视图页两层清单": ["必须一致", "必须不同", "多视图", "三视图"],
    "⑦体格与比例锚点": ["头身", "肩宽", "腿长占比", "7 个头高"],
    "⑧夸张表情→五官漂移": ["夸张表情", "眼型", "五官比例"],
    "⑨负向双向自查": ["双向自查", "风格本体", "污染"],
    "⑩场景性配件 vs 常驻特征": ["场景性配件", "每场都戴", "常驻"],
}


def counts(kws, files):
    tot = 0
    for kw in kws:
        for f in files:
            if not f.exists():
                continue
            tot += len(re.findall(re.escape(kw), f.read_text(encoding="utf-8")))
    return tot


print("=== 表1 规则落位审查（命中次数）===")
print(f"{'规则':34s} {'账本 LESSONS':>12s} {'主流程':>8s}   判断")
gap_rows = []
for name, kws in RULES.items():
    a = counts(kws, [LESSONS])
    b = counts(kws, MAIN)
    if b == 0 and a > 0:
        verdict = "✗ 只在账本里 → 必须升格"
    elif b > 0 and a > 0:
        verdict = "~ 两边都有"
    elif b == 0 and a == 0:
        verdict = "- 都还没有（新规则/不存在）"
    else:
        verdict = "✓ 已在主流程"
    print(f"{name:34s} {a:12d} {b:8d}   {verdict}")
    gap_rows.append((name, a, b, verdict))

print()
gap = [r for r in gap_rows if r[3].startswith("✗")]
print(f"→ 结论：{len(gap)} 条规则**仅存在于账本**，主流程完全看不到：")
for n, a, b, _ in gap:
    print(f"     {n}（账本命中 {a} 次，主流程 0 次）")

print()
print("=== 表2 生成时间线（来自 pending_urls.json 的实际时间戳）===")
p = Path("style-distill/round_lib/pending_urls.json")
if p.exists():
    rows = json.loads(p.read_text(encoding="utf-8"))
    for r in rows:
        print(f"  {r['ts']}  {'done ' if r['status']=='done' else r['status']:<5s} {Path(r['out']).name}")

print()
print("=== 表3 本次实测的下载速率点（KB/s）===")
speeds = [("2K 那张首次探测", 1.26), ("4K 那张首次探测", 97.2), ("4K 成功那次", 19.1),
          ("2K 成功那次", 18.1), ("v15 成功那次", 18.1), ("v16 成功那次", 14.6),
          ("雪景那张成功那次", 11.5), ("HTTP/1.1 复测", 13.2), ("浏览器 UA", 3.9),
          ("最低观测", 0.5)]
for lab, v in sorted(speeds, key=lambda t: t[1]):
    print(f"  {v:7.2f}  {lab}")
print(f"  → 极差 {max(v for _,v in speeds)/min(v for _,v in speeds):.0f} 倍（最高 97.2 / 最低 0.5）")
