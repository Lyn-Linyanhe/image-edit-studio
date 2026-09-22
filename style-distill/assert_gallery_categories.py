"""分类回归断言：40 个样本，覆盖审计中发现过的错误与各桶代表。

用**模块自己的分类器**（单一事实来源）。任何一条不符即退出码 1。
样本里刻意包含审计时被分错的那几个（round_lib、original、_smoke_、_cmp_B_no_mask、
_mask_guide），防止规则被改回去。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("mea", ROOT / "compose/images/mask_edit_app.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

CASES = [
    # ---- 成果
    ("style-distill/round_manga/out_v12B.png", "deliver", "轮次根层产出"),
    ("style-distill/round_manga/out_4kL_3840x2160.png", "deliver", "轮次根层产出"),
    ("style-distill/round_snow/out_B1_1536x1024.png", "deliver", "轮次根层产出"),
    ("style-distill/round_arcade/out_v2_r4_wink.png", "deliver", "候选成图（在轮次根层）"),
    ("compose/deliver/01_result.png", "deliver", "旧管线成品"),
    ("compose/final/result.png", "deliver", "旧管线成品"),
    ("compose/out/02_result.png", "deliver", "旧管线成品"),
    # ---- 局部
    ("style-distill/round_snow/work/mask_hair.png", "detail", "蒙版素材"),
    ("style-distill/target_t2/mask.png", "detail", "蒙版素材"),
    ("style-distill/target_t2/mask_vis.png", "detail", "蒙版可视化"),
    ("style-distill/round_manga/work/line_mask_preview.png", "detail", "线稿蒙版预览"),
    ("compose/final/mask_preview.png", "detail", "蒙版预览"),
    ("compose/final2/mask_preview.png", "detail", "蒙版预览"),
    ("compose/deliver/04_mask_guide.png", "detail", "蒙版引导图"),
    ("style-distill/round_snow/work/_zoom_mask_face.png", "detail", "局部放大对照"),
    ("style-distill/round_snow/work/_masktest2_zoom.png", "detail", "局部放大对照"),
    ("style-distill/round_snow/work/_warn.redmark.png", "detail", "涂红预览"),
    ("style-distill/round_snow/lab/out_r5c_repeat.redmark.png", "detail", "涂红预览"),
    ("style-distill/round_snow/lab/out_r5c_primary.png", "detail", "局部改图实验件"),
    ("style-distill/round_snow/lab/out_masktest2_1k.png", "detail", "局部改图实验件"),
    # ---- 过程（含审计时被分错的）
    ("style-distill/round_lib/out_r1.png", "process", "round_lib 不是轮次目录"),
    ("style-distill/round_lib/out_r7.png", "process", "round_lib 不是轮次目录"),
    ("compose/deliver/03_original.png", "process", "原图不是成果"),
    ("compose/deliver/05_side_by_side.png", "process", "对照图不是成果"),
    ("compose/deliver/02_background_only.png", "process", "背景层不是成果"),
    ("style-distill/round_snow/work/_smoke_sheet.png", "process", "冒烟测试残留"),
    ("style-distill/round_snow/work/_smoke_crop.png", "process", "冒烟测试残留"),
    ("style-distill/round_manga/checks/v13_compare.png", "process", "对照拼版"),
    ("style-distill/round_manga/checks/v11_faces_vs_ref.png", "process", "对照拼版"),
    ("compose/images/_cmp_B_no_mask.png", "process", "无遮罩对照组"),
    ("compose/images/_ab_A_visual_mask_2nd_ref.png", "process", "A/B 实验件"),
    ("style-distill/round_snow/work/_sent_mask.png", "process", "投喂件"),
    ("style-distill/round_snow/work/_sent_mask_big_content.png", "process", "投喂件（内容图）"),
    ("style-distill/round_manga/work/feed_A.png", "process", "投喂输入"),
    ("style-distill/round_manga/work/out_threeview_v9.png", "process", "work 里的迭代产出"),
    ("style-distill/round_arcade/input/B_char_style.png", "process", "参考输入"),
    ("compose/charsheet/01.png", "process", "旧管线杂项"),
    ("style-distill/round_manga/ref_xiami/x1.png", "process", "参考组"),
    ("style-distill/_probe/sheet_checks.png", "process", "审阅拼版（草稿区）"),
]

bad = 0
for rel, want, why in CASES:
    got = mod.gallery_category(rel)
    ok = got == want
    bad += 0 if ok else 1
    print(f"  {'OK ' if ok else '!! '} {got:8s} 期望 {want:8s} {rel:62s} （{why}）")
print(f"\n  → {len(CASES) - bad}/{len(CASES)} 通过" + ("" if bad == 0 else "  ← 有回归"))
sys.exit(0 if bad == 0 else 1)
