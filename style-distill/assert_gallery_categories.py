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
    # ---- 成果（README 里带 ✓ 的已认可交付件 + 旧管线成品）
    ("style-distill/round_manga/out_v12B.png", "deliver", "README 有 ✓"),
    ("style-distill/round_manga/out_v12B_lineLighter_s1.png", "deliver", "README 有 ✓"),
    ("style-distill/round_manga/out_4kL_3840x2160.png", "deliver", "README 有 ✓"),
    ("style-distill/round_snow/out_A1_1k.png", "deliver", "README 有 ✓"),
    ("style-distill/round_snow/out_B1_1536x1024.png", "deliver", "README 有 ✓"),
    ("compose/deliver/01_result.png", "deliver", "旧管线成品"),
    ("compose/final/result.png", "deliver", "旧管线成品"),
    ("compose/out/02_result.png", "deliver", "旧管线成品"),
    # ---- 候选（轮次根层 out_* 但 README 里没有 ✓）
    ("style-distill/round_arcade/out_v1_r1.png", "candidate", "候选表里、无 ✓"),
    ("style-distill/round_arcade/out_v2_r4_wink.png", "candidate", "候选表里、无 ✓"),
    ("style-distill/round_arcade/out_v2_r2_idanchor.png", "candidate", "候选表里、无 ✓"),
    # ---- 输入：**只计入最近一次会话里的上传**（用户要求"之前的都不计入"）
    ("style-distill/round_arcade/input/A_pose_env.png", "input", "最近一次上传（街机轮的图1）"),
    ("style-distill/round_arcade/input/B_char_style.png", "input", "最近一次上传（街机轮的图2）"),
    # ---- 更早的上传按切点不计入，落回各自规则
    ("style-distill/round_manga/input/A_char.png", "process", "更早的上传，不计入；input 里 A 前缀不构成参考"),
    ("style-distill/round_manga/input/B_manga.png", "reference", "更早的上传，不计入；input 里 B＝参考"),
    ("style-distill/round_snow/input/C_snow.jpg", "process", "更早的上传，不计入"),
    ("style-distill/round_manga/input/c1dc05a287896769311f364517a30509_720.jpg", "process",
     "更早的上传（与 C_snow.jpg 同源），不计入"),
    ("style-distill/round_lib/input/A_pose_style.png", "reference", "更早的上传，不计入；名字明示 pose_style"),
    ("style-distill/round_lib/input/B_char.png", "reference", "更早的上传，不计入；input 里 B＝参考"),
    ("style-distill/round_lib/out_r7.png", "process", "更早的上传同源，不计入；round_lib 不是轮次目录"),
    ("style-distill/round_manga/ref_xiami/R1_cheer.png", "reference", "更早的上传，不计入；参考目录"),
    ("style-distill/round_manga/ref_xiami/R3_clean.png", "reference", "更早的上传，不计入；参考目录"),
    ("style-distill/target_t2/input.png", "process", "更早的上传，不计入"),
    # ---- 参考（我派生/准备的参考件，与"输入"区分开）
    ("style-distill/round_manga/ref_xiami/R1_head.png", "reference", "我的裁切派生 → 参考"),
    ("style-distill/round_manga/ref_xiami/identity_face_gray.png", "reference", "灰度派生"),
    ("style-distill/target/pose_ref/pose_head.png", "reference", "姿态参考（派生裁切）"),
    ("style-distill/target/pose_ref2/p2_torso_full.png", "reference", "姿态参考（派生裁切）"),
    ("compose/style_ref.png", "reference", "风格参考"),
    ("style-distill/round_arcade/input/D_face_closeup.png", "reference", "我裁的脸部特写（派生）"),
    ("style-distill/_probe/style_ref.png", "process", "草稿区优先于参考判定"),
    ("style-distill/round_snow/input/C_snow_169.png", "process", "我裁的比例版（派生，不是你的原图）"),
    ("style-distill/round_manga/checks/ref_three_views.png", "compare", "名字带 ref 但属对照件"),

    # ---- 局部
    ("style-distill/round_snow/work/mask_hair.png", "detail", "蒙版素材"),
    ("style-distill/target_t2/mask.png", "detail", "蒙版素材"),
    ("style-distill/target_t2/mask_vis.png", "detail", "蒙版可视化"),
    ("style-distill/round_manga/work/line_mask_preview.png", "detail", "线稿蒙版预览"),
    ("compose/final/mask_preview.png", "detail", "蒙版预览"),
    ("compose/deliver/04_mask_guide.png", "detail", "蒙版引导图"),
    ("style-distill/round_snow/work/_zoom_mask_face.png", "detail", "局部放大对照"),
    ("style-distill/round_snow/work/_masktest2_zoom.png", "detail", "名字以 zoom 结尾"),
    ("style-distill/round_snow/work/_warn.redmark.png", "detail", "涂红预览"),
    ("style-distill/round_snow/lab/out_r5c_repeat.redmark.png", "detail", "涂红预览"),
    ("style-distill/round_snow/lab/out_r5c_primary.png", "detail", "局部改图实验件"),
    ("style-distill/round_snow/lab/out_masktest2_1k.png", "detail", "局部改图实验件"),
    # ---- 对照
    ("style-distill/round_manga/checks/v13_compare.png", "compare", "checks 目录"),
    ("style-distill/round_manga/checks/v11_faces_vs_ref.png", "compare", "checks 目录"),
    ("compose/images/_cmp_B_no_mask.png", "compare", "对照件（_cmp）"),
    ("compose/images/_ab_A_visual_mask_2nd_ref.png", "compare", "对照件（_ab_）"),
    ("compose/deliver/05_side_by_side.png", "compare", "左右对照图"),
    # ---- 过程（含历次审计中被分错的样本，防规则被改回）
    ("style-distill/round_lib/out_r1.png", "process", "round_lib 不是轮次目录（out_r7 也同为过程，因其上传已被切点排除）"),
    ("compose/deliver/03_original.png", "process", "原图不是成果"),
    ("compose/deliver/02_background_only.png", "process", "背景层不是成果"),
    ("compose/final/result_bg.png", "process", "背景层不是成果"),
    ("style-distill/round_snow/work/_smoke_sheet.png", "process", "冒烟残留（优先级高于对照）"),
    ("style-distill/round_snow/work/_smoke_crop.png", "process", "冒烟残留"),
    ("style-distill/round_snow/work/_dry2.redmark.png", "process", "试发送残留（优先级高于局部）"),
    ("style-distill/round_snow/work/_sent_mask.png", "process", "投喂件"),
    ("style-distill/round_snow/work/_sent_mask_big_content.png", "process", "投喂件（内容图）"),
    ("style-distill/round_manga/work/feed_A.png", "process", "投喂输入"),
    ("style-distill/round_manga/work/out_threeview_v9.png", "process", "work 里的迭代产出"),
    ("style-distill/round_arcade/input/B_char_style.png", "input", "你的上传 1789571251371.png（曾误判为参考）"),
    ("compose/charsheet/01.png", "process", "旧管线杂项"),
    ("style-distill/round_manga/ref_xiami/R1_head.png", "reference", "参考目录 ref_xiami（本轮新增页签后改判）"),
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
