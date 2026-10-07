"""系列批量验收：对目录中每张图跑 WD14 打标＋调色板＋亮区色＋edge，对照模板产出汇总。

用法：
    python series_audit.py <模板图> <系列目录> [--out 汇总.json]

输出：
    per-image json（.zimage/work/series-audit/<tag>.json）＋汇总表（终端）。
判读规则内建：
    - 重合率与内容发散正相关，看差异清单合理性；
    - 跨内容按「亮区色」判读（全图亮度 top 20% 像素的均色）。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

for s in (sys.stdout, sys.stderr):
    try:
        s.reconfigure(encoding="utf-8")
    except Exception:
        pass

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import colorgram  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402


def sha12(p: Path) -> str:
    import hashlib
    return hashlib.sha1(p.read_bytes()).hexdigest()[:12]


def palettes(path: Path, n: int = 6) -> list[str]:
    return [f"#{c.rgb.r:02x}{c.rgb.g:02x}{c.rgb.b:02x}" for c in colorgram.extract(str(path), n)]


def bright_zone_color(path: Path, top: float = 0.20) -> str:
    """全图亮度 top N% 像素的均色（人物/高亮区近似）。"""
    im = Image.open(path).convert("RGB").resize((256, 256))
    a = np.asarray(im, dtype=np.float32)
    lum = a.mean(axis=2)
    cut = np.quantile(lum, 1 - top)
    sel = lum >= cut
    mean = a[sel].mean(axis=0).astype(int)
    return "#{:02x}{:02x}{:02x}".format(*mean)


def edge_density(path: Path) -> tuple[float, float]:
    g = np.asarray(Image.open(path).convert("L"), dtype=np.float32)
    gx = np.abs(np.diff(g, axis=1))[:-1, :]
    gy = np.abs(np.diff(g, axis=0))[:, :-1]
    grad = np.maximum(gx, gy)
    return round(float((grad > 12).mean()) * 100, 2), round(float((grad > 30).mean()) * 100, 2)


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("template")
    ap.add_argument("series_dir")
    ap.add_argument("--out", default=".zimage/work/series-audit")
    a = ap.parse_args()

    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    from wdtagger import Tagger
    tagger = Tagger()
    t_tags = set(t for t, p in tagger.tag(Image.open(a.template).convert("RGB")).general_tag_data.items() if p >= 0.35)

    rows = []
    for f in sorted(Path(a.series_dir).glob("*.png")) + sorted(Path(a.series_dir).glob("*.jpg")):
        if f.stem.endswith(("-REJECTED",)):
            continue
        result = tagger.tag(Image.open(f).convert("RGB"))
        o_tags = set(t for t, p in result.general_tag_data.items() if p >= 0.35)
        inter = len(t_tags & o_tags)
        union = len(t_tags | o_tags)
        weak, strong = edge_density(str(f))
        row = {
            "file": f.name,
            "重合率": round(inter / max(union, 1), 3),
            "共同标签数": inter,
            "仅模板数": len(t_tags - o_tags),
            "仅产出数": len(o_tags - t_tags),
            "调色板": palettes(f),
            "亮区色": bright_zone_color(f),
            "edge弱": weak,
            "edge强": strong,
        }
        rows.append(row)
        (out_dir / f"{f.stem}.json").write_text(
            json.dumps(row, ensure_ascii=False, indent=1), encoding="utf-8")

    template_bright = bright_zone_color(a.template)
    print(json.dumps({
        "模板亮区色": template_bright,
        "汇总": [{k: r[k] for k in ("file", "重合率", "亮区色", "edge弱", "edge强")} for r in rows],
    }, ensure_ascii=False, indent=1))
    (out_dir / "summary.json").write_text(
        json.dumps({"模板亮区色": template_bright, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
