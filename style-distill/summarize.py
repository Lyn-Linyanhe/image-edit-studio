import json
from pathlib import Path

d = json.load(open(Path("style-distill/style_stats.json"), encoding="utf-8"))
print("file      sat    p90   lum5%   wash   edge  paper      ink     top hues")
for s in d["per_image"]:
    top = sorted(s["hue_family"].items(), key=lambda kv: -kv[1])[:3]
    tops = " ".join(f"{k}:{v:.2f}" for k, v in top)
    print(
        f"{s['file'][:8]} {s['sat_mean_content']:.3f} {s['sat_p90_content']:.3f} "
        f"{s['lum_p05']:.3f} {s['wash_ratio']:.3f} {s['edge_density']:5.2f} "
        f"{s['paper_white_ratio']:.3f} {s['ink_line_color']}  {tops}"
    )

print("\nper-image top-5 palette:")
for f, p in d["aggregate"]["per_image_palette"].items():
    print(f[:8], " ".join(f"{c['hex']}({c['share']:.2f})" for c in p))
