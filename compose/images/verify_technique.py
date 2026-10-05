"""Did we get 'technique changed, colour preserved'?

Compares the ORIGINAL 灰绿 reference against the generated TECH_1.png on:
  - palette  (mean RGB, cool/warm cast)        -> must stay close
  - saturation                                -> must stay close
  - micro-detail / edge energy                -> should RISE if linework got
                                                 bolder and edges crisper
Edge energy is measured two ways so a resolution change cannot fake it:
  * mean |Laplacian| normalised by std (scale-independent sharpness)
  * fraction of pixels whose local contrast exceeds a threshold
"""
import numpy as np
import os as _os
_MANTU_ROOT_STR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *([".."] * 2)))
from PIL import Image, ImageFilter

SRC = f"{_MANTU_ROOT_STR}/compose/style_ref.png"
OUT = f"{_MANTU_ROOT_STR}/compose/out/TECH_1.png"
RED = f"{_MANTU_ROOT_STR}/compose/input_red.jpg"


def load(p, size=None):
    im = Image.open(p).convert("RGB")
    if size:
        im = im.resize(size, Image.LANCZOS)
    return np.asarray(im).astype(np.float32)


def stats(a, label):
    sat = a.max(axis=2) - a.min(axis=2)
    g = a.mean(axis=2)
    lap = np.asarray(Image.fromarray(g.astype(np.uint8)).filter(
        ImageFilter.FIND_EDGES)).astype(np.float32)
    # scale-independent: edge response relative to overall contrast
    edge_norm = lap.mean() / max(g.std(), 1e-6)
    strong = (lap > 40).mean() * 100
    print(f"{label:26s} mean {a.reshape(-1,3).mean(axis=0).round(0)}  "
          f"L {g.mean():5.1f}  std {g.std():5.1f}  sat {sat.mean():5.1f}  "
          f"edge/std {edge_norm:5.2f}  strong-edge {strong:5.2f}%")
    return dict(mean=a.reshape(-1, 3).mean(axis=0), L=g.mean(), std=g.std(),
                sat=sat.mean(), edge=edge_norm, strong=strong)


size = (1024, 1536)
src = load(SRC, size)
out = load(OUT)
red = load(RED, size)

print("=== palette & technique ===")
s_src = stats(src, "灰绿 原图 (resized)")
s_out = stats(out, "TECH_1 结果")
s_red = stats(red, "红发 风格源 (resized)")

print("\n=== did colour survive? (lower = closer to the original) ===")
d_mean = np.abs(s_out["mean"] - s_src["mean"]).mean()
print(f"  mean RGB shift      : {d_mean:5.1f}   (target: small, <10 is excellent)")
print(f"  luminance shift     : {abs(s_out['L'] - s_src['L']):5.1f}")
print(f"  contrast ratio      : out/std={s_out['std']:.1f} vs src/std={s_src['std']:.1f}"
      f"  -> {s_out['std']/max(s_src['std'],1e-6):.2f}x")
print(f"  saturation ratio    : out={s_out['sat']:.1f} vs src={s_src['sat']:.1f}"
      f"  -> {s_out['sat']/max(s_src['sat'],1e-6):.2f}x   (1.0 = unchanged)")

print("\n=== did technique change? (edge energy should RISE toward the red source) ===")
print(f"  edge/std: src={s_src['edge']:.2f}  out={s_out['edge']:.2f}  red={s_red['edge']:.2f}")
if s_out["edge"] > s_src["edge"]:
    print(f"  -> sharper/cleaner edges: +{(s_out['edge']/s_src['edge']-1)*100:.0f}%")
else:
    print(f"  -> edges got SOFTER: {(s_out['edge']/s_src['edge']-1)*100:.0f}%")
print(f"  strong-edge area: src={s_src['strong']:.2f}%  out={s_out['strong']:.2f}%  "
      f"red={s_red['strong']:.2f}%")

# colour drift per channel tells us if it went warm (red) or cool
print("\n=== cast check ===")
for lbl, s in (("src", s_src), ("out", s_out)):
    m = s["mean"]
    print(f"  {lbl}: R{m[0]:.0f} G{m[1]:.0f} B{m[2]:.0f}  "
          f"{'warm (R>B)' if m[0]-m[2] > 6 else 'neutral/olive' if abs(m[0]-m[2]) <= 6 else 'cool (B>R)'}")
