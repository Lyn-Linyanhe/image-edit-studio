"""第 3 步 · 投喂前预处理（本轮）

按 R5：图1 里"输出不该出现"的显著元素必须**在图上物理抹掉**，负向词删不掉。
本轮抹两样：① 正中那块无法识别的**橙色圆润物**；② 格内的**中文字幕**。
另外裁成单格，去掉"上下两格"这个版式先验（输出是三视图原稿页，留着双格先验会把结果往两格上拽）。

⚠️ 教训：第一版用**颜色规则**自动定位橙色物 → 整幅图是暖金色强光，
"R 高、R-B 大"把脸、头发、手臂全匹配进去了，擦完一片糊。
**改用手工坐标框**（位置从网格图量得），不再用颜色规则。

抹完必须**中和**：否则 inpaint 用周围颜色补出的平滑色块会被模型当成身体部位
（这个坑吃过一次：笔记本擦完长出一条假胳膊）。

用法：python prep_char.py
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
SRC = HERE / "input" / "A_char.png"

CROP = (200, 0, 1000, 674)          # 原图坐标：落在顶格内，含脸/眼镜/领结/荷叶边/挂件

# 原图坐标下的擦除框（从顶格网格图量得）
# ⚠️ 橙色物**故意不擦**：两次尝试都失败——
#    ① 颜色规则：整幅是暖金强光，"R 高/R-B 大"把脸、头发、手臂全匹配进去，擦完一片糊；
#    ② 手工坐标框：它紧贴并部分叠在她的躯干上，框小了擦不净、框大了要伤到
#       蓝色荷叶边/白色上衣/粉色挂件这些身份内容，而它是**未识别**的东西。
#    判断：本轮输出是**全新三视图 + 黑白**，橙色物作为"颜色"不可能残留，
#    最多残留形状；留着它、由提示词层面明确不带，比冒着毁掉身份内容的风险去擦更划算。
ERASE_BOXES_ORIG = [
    (398, 542, 724, 668),           # 中文字幕「我是新生」（框比文字外扩并下移，避免残影）
]


def main() -> int:
    rgb_full = np.asarray(Image.open(SRC).convert("RGB"))
    x0, y0, x1, y1 = CROP
    rgb = rgb_full[y0:y1, x0:x1].copy()
    print(f"  裁剪 {CROP} -> {rgb.shape[1]}x{rgb.shape[0]}")

    h, w = rgb.shape[:2]
    mask = np.zeros((h, w), np.uint8)
    for (sx0, sy0, sx1, sy1) in ERASE_BOXES_ORIG:
        bx0, by0 = max(0, sx0 - x0), max(0, sy0 - y0)
        bx1, by1 = min(w, sx1 - x0), min(h, sy1 - y0)
        if bx1 <= bx0 or by1 <= by0:
            print(f"  ! 框 {sx0},{sy0},{sx1},{sy1} 落在裁剪范围外，已跳过")
            continue
        mask[by0:by1, bx0:bx1] = 255
        print(f"  擦除框 -> 裁剪内 ({bx0},{by0})-({bx1},{by1})")
    if not mask.any():
        raise SystemExit("掩膜为空，检查坐标")

    mask = cv2.dilate(mask, np.ones((13, 13), np.uint8))
    covered = int((mask > 0).sum())
    print(f"  掩膜覆盖 {covered} px / {h*w} px = {covered/(h*w)*100:.1f}%（上一版是 19%，请对照）")

    cleaned = cv2.inpaint(rgb, mask, 61, cv2.INPAINT_TELEA)
    cleaned = cv2.medianBlur(cleaned, 5).astype(np.float32)

    bg = rgb_full[20:80, 20:80].reshape(-1, 3).mean(axis=0)
    soft = cv2.GaussianBlur(mask.astype(np.float32) / 255.0, (0, 0), 24)
    soft = np.clip(soft * 1.6, 0, 1)[..., None]
    gray = cleaned.mean(axis=2, keepdims=True)
    desat = cleaned * 0.35 + gray * 0.65
    target = desat * 0.45 + bg.reshape(1, 1, 3) * 0.55
    out = np.clip(cleaned * (1 - soft) + target * soft, 0, 255).astype(np.uint8)

    (HERE / "work").mkdir(exist_ok=True)
    Image.fromarray(out).save(HERE / "work" / "feed_char_clean.png", optimize=True)

    vis = rgb.copy()
    vis[mask > 0] = (0.4 * vis[mask > 0] + 0.6 * np.array([255, 0, 0])).astype(np.uint8)
    S = 560
    def rs(im):
        return Image.fromarray(im).resize((S, int(S * im.shape[0] / im.shape[1])), Image.LANCZOS)
    before, mark, after = rs(rgb), rs(vis), rs(out)
    H = max(before.height, mark.height, after.height)
    c = Image.new("RGB", (S * 3 + 32, H + 24), (255, 255, 255))
    d = ImageDraw.Draw(c)
    for i, (t, im) in enumerate([("after CROP", before), ("ERASE MASK", mark), ("CLEANED", after)]):
        c.paste(im, (i * (S + 16), 24))
        d.text((i * (S + 16) + 6, 6), t, fill=(200, 0, 0))
    c.save(HERE / "prep_check.png")
    print(f"  -> work/feed_char_clean.png {out.shape[1]}x{out.shape[0]}")
    print("  -> prep_check.png 请核对：脸/眼镜/领结/荷叶边/挂件必须完好，橙色物与字幕必须消失")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
