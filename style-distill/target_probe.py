"""目标图专项剖析：写 PRESERVE 段需要的逐项事实。"""
import json
import numpy as np
from PIL import Image
from pathlib import Path

p = Path("style-distill/target/target.png")
im = Image.open(p).convert("RGB")
W, H = im.size
rgb = np.asarray(im, dtype=np.float64) / 255.0
hsv = np.asarray(im.convert("HSV"), dtype=np.float64) / 255.0
lum = rgb.mean(axis=2)
h, s, v = hsv[..., 0] * 360, hsv[..., 1], hsv[..., 2]

st = json.load(open("style-distill/target/target_stats.json", encoding="utf-8"))["per_image"][0]
print(f"尺寸 {W}x{H}  比例 {W/H:.3f}")
print(f"lum_min {st['lum_p05']:.3f}(P05)  实测最暗 {lum.min():.3f}  明度均值 {lum.mean():.3f}")
print(f"内容饱和度 {st['sat_mean_content']:.3f}")

print("\n高饱和蓝/青像素（蓝眼、蓝羽、蓝宝石、蓝发夹）：")
blue = ((h >= 190) & (h <= 260) & (s > 0.25))
print(f"  s>0.25 的蓝像素占比 {blue.mean()*100:.3f}%  数量 {blue.sum()}")
if blue.sum():
    ys, xs = np.nonzero(blue)
    m = rgb[blue].mean(axis=0)
    print("  平均色 #%02X%02X%02X" % tuple(int(round(c*255)) for c in m))
    print(f"  纵向分布 y: {np.percentile(ys,[5,50,95]).round(0)} (H={H})")
    print(f"  横向分布 x: {np.percentile(xs,[5,50,95]).round(0)} (W={W})")
    # 分簇看大致位置
    print("  蓝像素 y 分带占比: " + " ".join(
        f"{lo}-{hi}:{blue[int(lo/100*H):int(hi/100*H)].mean()*100:.2f}%" for lo, hi in [(0,20),(20,40),(40,60),(60,80),(80,100)]))

print("\n发色（上部 25% 且偏暖的中亮区）:")
top = np.zeros_like(lum, bool); top[:int(0.25*H)] = True
hair = top & (lum > 0.55) & (lum < 0.85) & (((h <= 60) | (h >= 340)))
if hair.sum():
    m = rgb[hair].mean(axis=0)
    print("  均值 #%02X%02X%02X  占比 %.1f%%" % (*[int(round(c*255)) for c in m], hair.mean()*100))

print("\n背景区（人物轮廓外围, 左右各 18% 带宽）:")
bw = int(0.18*W)
left = lum[:, :bw]; right = lum[:, -bw:]
for name, band in [("左带", left), ("右带", right)]:
    print(f"  {name}: 明度均值 {band.mean():.3f}  最暗 {band.min():.3f}  面积占比 {band.size/lum.size*100:.0f}%")
bl = rgb[:, :bw].reshape(-1,3); 
print("  左带均值色 #%02X%02X%02X" % tuple(int(round(c*255)) for c in bl.mean(axis=0)))
br = rgb[:, -bw:].reshape(-1,3)
print("  右带均值色 #%02X%02X%02X" % tuple(int(round(c*255)) for c in br.mean(axis=0)))

print("\n明度直方图（每 10% 一档, 占比）:")
for i in range(10):
    lo, hi = i/10, (i+1)/10
    print(f"  {lo:.1f}-{hi:.1f}: {( (lum>=lo)&(lum<hi) ).mean()*100:5.2f}%")
print(f"  亮度<0.20 占比: {(lum<0.20).mean()*100:.3f}%")
print(f"  亮度<0.35 占比: {(lum<0.35).mean()*100:.3f}%")
