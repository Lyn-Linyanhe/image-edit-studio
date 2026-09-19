"""生成色板对照图：全组主色阶 + 三套变体 + 信号色。"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhl.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
]


def load_font(size: int):
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


F_TITLE = load_font(21)
F_VAR = load_font(17)
F_HEX = load_font(15)
F_SMALL = load_font(14)

GLOBAL = [
    ("#F2EBED", "14.1%"), ("#E3DEE3", "12.8%"), ("#D5CFD6", "11.4%"),
    ("#C3BFC3", "10.6%"), ("#B3B0B7", "10.1%"), ("#A3A0AB", "10.5%"),
    ("#9190A1", "10.1%"), ("#857F93", "8.9%"), ("#787084", "7.3%"),
    ("#635B70", "4.1%"),
]
VARIANTS = [
    ("A 鼠尾草米白", ["#F0E9E6", "#DAD3D4", "#BAB7B2", "#9FA09B", "#7D7C77"]),
    ("B 薰衣草灰紫", ["#E4DAE7", "#C2B9D0", "#A89DBA", "#877A96", "#6A607F"]),
    ("C 藏青石墨", ["#E5E5F0", "#CCCCDB", "#ABACBB", "#8C90A3", "#696775"]),
]
SIGNALS = [
    ("#F4D7DA", "腮红/唇 13/13"), ("#AB737E", "红电话 1/13"),
    ("#ED9AA8", "草莓 1/13"), ("#4E455A", "线稿最暗"), ("#74716F", "线稿最亮"),
]

W, H = 1180, 760
BG = "#FFFFFF"
TXT = "#2B2B2B"
SUB = "#7A7A7A"

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

y = 28
d.text((30, y), "全组主色阶 (OKLab k-means, 13 张, 按面积占比)", fill=TXT, font=F_TITLE)
y += 34
sw = (W - 60) / len(GLOBAL)
for i, (hexv, share) in enumerate(GLOBAL):
    x = 30 + i * sw
    d.rectangle([x, y, x + sw - 3, y + 96], fill=hexv, outline="#E2E2E2")
    d.text((x + 2, y + 100), hexv, fill=SUB, font=F_SMALL)
    d.text((x + 2, y + 117), share, fill="#A8A8A8", font=F_SMALL)
y += 156

d.text((30, y), "三套配色分支", fill=TXT, font=F_TITLE)
y += 34
for name, cols in VARIANTS:
    d.text((30, y + 18), name, fill=TXT, font=F_VAR)
    cw = (W - 300) / len(cols)
    for i, hexv in enumerate(cols):
        x = 270 + i * cw
        d.rectangle([x, y, x + cw - 5, y + 58], fill=hexv, outline="#E2E2E2")
        d.text((x + 2, y + 61), hexv, fill=SUB, font=F_SMALL)
    y += 92

d.text((30, y), "信号色 / 线稿色（全画唯一允许的暖色）", fill=TXT, font=F_TITLE)
y += 34
for i, (hexv, label) in enumerate(SIGNALS):
    x = 30 + i * 155
    d.rectangle([x, y, x + 118, y + 50], fill=hexv, outline="#E2E2E2")
    d.text((x, y + 54), label, fill=SUB, font=F_SMALL)
    d.text((x, y + 71), hexv, fill="#A8A8A8", font=F_SMALL)

out = Path("style-distill/palette.png")
img.save(out)
print("->", out.resolve(), img.size)
