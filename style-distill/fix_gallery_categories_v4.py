"""分类规则修正（审计断言抓出来的两条）：
  ① `_zoom_` 匹配不到名字以 zoom 结尾的（`_masktest2_zoom.png`）→ 改为 `_zoom` 并加后缀匹配；
  ② 旧管线 compose/ 没有交付清单，按"成品名"判：把图层与非成品名排除出"成果"
     （证据：deliver/02_background_only.png、final/result_bg.png、out2/01_bg_only.png
       三者字节数完全相同 340,810 B —— 同一个背景层被复用，属图层不是成品）。
"""
from __future__ import annotations

import pathlib
import py_compile
import sys

sys.stdout.reconfigure(encoding="utf-8")

P = pathlib.Path("compose/images/mask_edit_app.py")
t = P.read_text(encoding="utf-8")

pairs = [
    ('DETAIL_HINTS = ("redmark", "_zoom_")        # 涂红预览、局部放大对照',
     'DETAIL_HINTS = ("redmark", "_zoom")         # 涂红预览、局部放大对照\n'
     'DETAIL_SUFFIX = ("zoom",)                 # …_zoom.png 这类以 zoom 结尾的也算\n'
     '                                          # （审计抓出："_zoom_" 匹配不到名字末尾的 zoom）'),
    ('    if any(h in name for h in DETAIL_HINTS):\n        return "detail"',
     '    if (any(h in name for h in DETAIL_HINTS)\n'
     '            or name.rsplit(".", 1)[0].endswith(DETAIL_SUFFIX)):\n'
     '        return "detail"'),
    ('DELIVER_DENY = ("original", "preview", "side_by_side", "compare", "check", "mask")',
     '# 旧管线 compose/ 没有交付清单，只能按"成品名"判：以下名字是图层/原图/对照/检查，不算成果。\n'
     '# 依据：deliver/02_background_only.png、final/result_bg.png、out2/01_bg_only.png\n'
     '# 三者字节数完全相同（340,810 B）——同一个背景层被复用，属图层而非成品。\n'
     'DELIVER_DENY = ("original", "background_only", "bg_only", "bg", "mask", "preview",\n'
     '                "side_by_side", "compare", "check", "tech")'),
]

for old, new in pairs:
    n = t.count(old)
    print(f"  锚点命中 {n} 次：{old.strip().splitlines()[0][:58]}")
    assert n == 1, f"锚点命中 {n} 次 → 停止"
    t = t.replace(old, new)

P.write_text(t, encoding="utf-8")
py_compile.compile(str(P), doraise=True)
print("  已写入并编译通过")
