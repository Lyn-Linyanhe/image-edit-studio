"""给 run_round.py 加 --encode jpg（JPEG 投喂通道）。

锚点必须命中 1 次，否则立刻停（沿用 SKILL.md 的补丁纪律）。
"""
from __future__ import annotations

import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8")

P = pathlib.Path("style-distill/round_lib/run_round.py")
t = P.read_text(encoding="utf-8")

BUILD_JPG = '''

def build_jpg(content: Image.Image, refs: list[Image.Image], tw: int, th: int,
              pad: str, quality: int = 90) -> dict:
    """把所有投喂图归一化到目标尺寸后改用 **JPEG** 编码。

    2026-09-22 实测（1024×1536，两张高细节彩图）：
      PNG：内容 1.54 + 参考 1.26 = **2.80 MiB**（超 1.96 上限，只能走压缩梯子的低质档）
      JPEG q88：内容 0.31 + 参考 0.24 = **0.56 MiB** —— 差约 5 倍。
    原因是 PNG 无损，而投喂前会先把图 **放大** 到目标尺寸（放大破坏量化/调色板结构，
    所以"先本地量化降熵"实测几乎无效：2.80 → 2.73 MiB）。
    好处不只是过闸：**不必再把身份参考压成 448px+模糊+128色**（那正是"脸不像"的根源）。
    """
    from mask_edit_app import normalise_to_size      # noqa: WPS433

    def enc(im: Image.Image) -> bytes:
        b = io.BytesIO()
        normalise_to_size(im.convert("RGB"), tw, th, pad).save(
            b, "JPEG", quality=quality, optimize=True)
        return b.getvalue()

    files = {"image": ("image.jpg", enc(content), "image/jpeg")}
    for i, r in enumerate(refs, start=1):
        files[f"image[{i}]"] = (f"ref{i}.jpg", enc(r), "image/jpeg")
    return files


def _fmt_sec(sec: float) -> str:'''

pairs = [
    # 1) 新增 build_jpg
    ("\n\ndef _fmt_sec(sec: float) -> str:", BUILD_JPG),
    # 2) run_one 签名加两个参数
    ("            mask_invert: bool = False, mask_primary: bool = False) -> int:",
     "            mask_invert: bool = False, mask_primary: bool = False,\n"
     "            encode: str = \"png\", jpg_quality: int = 90) -> int:"),
    # 3) 整图分支走 JPEG
    ("""    else:
        c2, r2, note = pick_reduction(content, refs, tw, th, pad, budget)
        print(f"  压缩策略: {note}", flush=True)
        files, _fit = G.build_whole(c2, tw, th, pad, style=r2)
        total = sum(len(v[1]) for v in files.values())
        print(f"  发送 {total} B = {total/1048576:.2f} MiB  files={list(files)}", flush=True)""",
     """    else:
        if encode == "jpg":
            # JPEG 通道：不经压缩梯子（不需要——同尺寸下体积小一个数量级）
            files = build_jpg(content, refs, tw, th, pad, jpg_quality)
            note = f"JPEG q{jpg_quality}（不走压缩梯子）"
            print(f"  压缩策略: {note}", flush=True)
        else:
            c2, r2, note = pick_reduction(content, refs, tw, th, pad, budget)
            print(f"  压缩策略: {note}", flush=True)
            files, _fit = G.build_whole(c2, tw, th, pad, style=r2)
        total = sum(len(v[1]) for v in files.values())
        print(f"  发送 {total} B = {total/1048576:.2f} MiB  files={list(files)}", flush=True)"""),
    # 4) 台账记编码
    ('                "fields": list(files),',
     '                "fields": list(files), "encode": encode,'),
    # 5) CLI 参数
    ('    ap.add_argument("--mask-primary", action="store_true",',
     '    ap.add_argument("--encode", choices=["png", "jpg"], default="png",\n'
     '                    help="投喂编码：png（默认）或 jpg。**jpg 实测同尺寸下体积小约 5 倍**"\n'
     '                         "（1024×1536 两张高细节图：PNG 2.80 MiB → JPEG 0.56 MiB），"\n'
     '                         "因此不必再走低质压缩档；代价是屏幕类高频内容会有 JPEG 压缩痕迹")\n'
     '    ap.add_argument("--jpg-quality", type=int, default=90, help="--encode jpg 的质量，默认 90")\n'
     '    ap.add_argument("--mask-primary", action="store_true",'),
    # 6) 两处调用点透传
    ("                          mask_invert=a.mask_invert, mask_primary=a.mask_primary)",
     "                          mask_invert=a.mask_invert, mask_primary=a.mask_primary,\n"
     "                          encode=a.encode, jpg_quality=a.jpg_quality)"),
    ("                                  a.mask_invert, a.mask_primary)",
     "                                  a.mask_invert, a.mask_primary, a.encode, a.jpg_quality)"),
]

for old, new in pairs:
    n = t.count(old)
    print(f"  锚点命中 {n} 次：{old.strip().splitlines()[0][:60]}")
    assert n == 1, f"锚点命中 {n} 次 → 停止"
    t = t.replace(old, new)

P.write_text(t, encoding="utf-8")
print("  已写入", P)
