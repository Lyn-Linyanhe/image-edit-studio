"""修正画廊分类：按"看图核对"的结果重定规则。

看图后的结论（不是按文件名猜的）：
  · round_manga/checks/ 的 23 张全是**"输出 vs 参考"的对照条与诊断拼版** → 属"过程"，不是"局部"；
  · round_snow/work/_smoke_crop.png、_smoke_sheet.png 是**冒烟测试残留** → 属"过程"，不是"局部"；
  · mask_*.png（蒙版素材）、*redmark*.png（涂红预览）、*_zoom_*.png（局部放大对照）才是"局部"；
  · work/ 里同时有 feed_*（投喂输入）与 out_threeview_v*（迭代产出），一刀切都归"过程"是对的
    （都不是交付件）。
所以：
  局部 = round_*/lab 的局部改图实验件 + 蒙版素材 + 涂红预览 + 局部放大对照
  过程 = 其余（含 checks 的对照/诊断件、work 的一切、input、target*、compose 杂项、冒烟残留）
"""
from __future__ import annotations

import pathlib
import py_compile
import sys

sys.stdout.reconfigure(encoding="utf-8")

P = pathlib.Path("compose/images/mask_edit_app.py")
t = P.read_text(encoding="utf-8")

pairs = [
    ("DETAIL_DIRS = {\"lab\", \"checks\"}\n"
     "DETAIL_HINTS = (\"redmark\", \"_zoom_\", \"_sheet\", \"contact\", \"palette\", \"_crop\")",
     "# 局部：**看图核对过**的四类——局部改图实验件、蒙版素材、涂红预览、局部放大对照。\n"
     "# 注：checks/ 的对照拼版与 _smoke_* 冒烟残留**不属于**局部（已按图核对后移出）。\n"
     "DETAIL_DIRS = {\"lab\"}\n"
     "DETAIL_HINTS = (\"redmark\", \"_zoom_\")\n"
     "DETAIL_NAME_PREFIX = (\"mask\",)          # mask_hair.png / mask_vis.png …\n"
     "DETAIL_NAME_EXTRA = (\"mask_preview\",)     # line_mask_preview.png"),
    ("    if in_detail or any(h in name for h in DETAIL_HINTS):\n"
     "        return \"detail\"",
     "    if (in_detail or any(h in name for h in DETAIL_HINTS)\n"
     "            or name.startswith(DETAIL_NAME_PREFIX)\n"
     "            or any(h in name for h in DETAIL_NAME_EXTRA)):\n"
     "        return \"detail\""),
]

for old, new in pairs:
    n = t.count(old)
    print(f"  锚点命中 {n} 次：{old.strip().splitlines()[0][:60]}")
    assert n == 1, f"锚点命中 {n} 次 → 停止"
    t = t.replace(old, new)

P.write_text(t, encoding="utf-8")
py_compile.compile(str(P), doraise=True)
print("  已写入并编译通过")
