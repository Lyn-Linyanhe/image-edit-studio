"""端到端验收 --mask（修正版）。

上一版是错的：它把正方形输出直接缩回去和**未裁切的**原图比，
而 --pad 默认 crop 会先把源图**居中裁成目标比例**再投喂
（normalise_to_size 第 227-234 行）。所以那次比较是拿裁过的结果比没裁的输入，
"保护区改动更大"是方法错误造成的假象。

本版按管线真实路径重建"模型收到的那张图"，并让蒙版走同一条裁切。

用法：python verify_mask_e2e.py <输入> <输出> <蒙版> <请求宽> <请求高>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent          # 仓库根
for cand in (ROOT / "compose" / "images", ROOT / "compose"):
    if (cand / "mask_edit_app.py").exists():
        sys.path.insert(0, str(cand))
        break

IN, OUT, MASK = (Path(v) for v in sys.argv[1:4])
TW, TH = int(sys.argv[4]), int(sys.argv[5])
PAD = sys.argv[6] if len(sys.argv) > 6 else "crop"      # 必须与发送时用的一致，否则坐标系又对不上

try:
    from mask_edit_app import normalise_to_size          # 直接用被测代码本体
    src_mod = "mask_edit_app.normalise_to_size（被测代码本体）"
except Exception as e:                                    # 依赖缺失时退回等价实现
    print(f"  （导入 mask_edit_app 失败：{e}；退回等价实现）")
    def normalise_to_size(img, tw, th, pad_mode):
        img = img.convert("RGB")
        src_ar, tgt_ar = img.width / img.height, tw / th
        if src_ar > tgt_ar:
            nw = int(img.height * tgt_ar)
            box = ((img.width - nw) // 2, 0, (img.width - nw) // 2 + nw, img.height)
        else:
            nh = int(img.width / tgt_ar)
            box = (0, (img.height - nh) // 2, img.width, (img.height - nh) // 2 + nh)
        return img.crop(box).resize((tw, th), Image.LANCZOS)
    src_mod = "等价实现"

a = Image.open(IN).convert("RGB")
out = Image.open(OUT).convert("RGB")
m0 = Image.open(MASK).convert("L")

print(f"  原文 {a.size}   请求目标 {TW}x{TH}   实得输出 {out.size}   蒙版 {m0.size}")
print(f"  几何换算：{src_mod}")

fit = normalise_to_size(a, TW, TH, PAD)                # 模型真正收到的画面
if m0.size != a.size:
    m0 = m0.resize(a.size, Image.LANCZOS)
fitmask = normalise_to_size(m0, TW, TH, PAD)           # 蒙版走同一条归一化

print(f"  裁切后投喂 {fit.size}（原画幅被保留的比例：{fit.width/fit.height * a.height/a.width * 100:.0f}% 的宽度）")

o = out.resize((TW, TH), Image.LANCZOS)                   # 输出缩到同一坐标系
A = np.asarray(fit).astype(np.float32)
B = np.asarray(o).astype(np.float32)
M = np.asarray(fitmask.convert("L")) > 127        # normalise_to_size 回的是 RGB，取通道转回单通道

diff = np.abs(A - B).mean(axis=2)
inside, outside = diff[M], diff[~M]

print()
print("  【修正后的对比：输出 vs 模型实际收到的裁切图】")
print(f"    蒙版内（应被重画）: 均值 {inside.mean():6.2f}  中位 {np.median(inside):6.2f}  改动>30 占 {(inside>30).mean()*100:5.1f}%")
print(f"    蒙版外（应被保护）: 均值 {outside.mean():6.2f}  中位 {np.median(outside):6.2f}  改动>30 占 {(outside>30).mean()*100:5.1f}%")
r = inside.mean() / max(outside.mean(), 1e-6)
print(f"    比值 内/外 = {r:.2f}")

corr = np.corrcoef(np.asarray(fit.resize((96, 96))).mean(2).ravel(),
                   np.asarray(o.resize((96, 96))).mean(2).ravel())[0, 1]
print(f"    整体结构相关（96×96）= {corr:.3f}   （接近 1 ＝构图与像素基本一致）")

print()
print("  判据（**本脚本只给数字，不下结论**——2026-09-22 的教训：") 
print("   早先这里会根据「内/外比值」自动打印「蒙版通道有效」，而正向那几次的比值是靠")
print("   「外部恰好 0.00」这个分母撑出来的，真实情况是「整张图根本没改」。工具替人下结论会骗人。）")
print("  请连起来读，并**先确认「是不是发生了编辑」再谈保护**：")
print("    · 若 内、外 都≈0（且彼此接近）→ **整张图没改**：既不能说明蒙版在改，也不能说明它在保护；")
print("    · 若 外 明显大、内 接近 0      → 保护成立（可改区真的改了，保护区没动）；")
print("    · 若 内 明显大、外 接近 0      → 局部改图成立；")
print("    · 若 内≈外 且都明显大          → 整图被重画，保护没生效。")

# 对照：上一版错在哪（拿正方形输出硬缩回完整原图）
naive = np.abs(np.asarray(a).astype(np.float32) -
               np.asarray(out.resize(a.size, Image.LANCZOS)).astype(np.float32)).mean(axis=2)
print(f"\n  （对照）错算法（不按管线裁切对齐）会给出：全图平均 {naive.mean():.2f}"
      f"  —— 它把裁切造成的位移全算成了「改动」")
