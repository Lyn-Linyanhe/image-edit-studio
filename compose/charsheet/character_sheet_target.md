# 图2 人物特征锁（Character Sheet）

> 用途：换任何风格基准图时，把 **§1 + §2 + §3 + §4** 整段拼进 prompt 的 PRESERVE 段，再追加风格块。
> 所有条目均来自对 `base_v1.png`（= `style_ref.png`，837×1243，sha256 前缀 `7235AD0F9E15E10D`）的放大逐区确认，非推断。
> 坐标以 837×1243 为准，写法为 `(x, y)`；比例系数按目标输出尺寸等比换算。

---

## §1 复制定位句（IDENTITY BANNER · 每轮必带，放最前）

```
This image is a STYLE TRANSFER of an existing character design, not a redesign and not a new
character. The character's face, hair, body, pose, framing and every listed accessory must be
reproduced from the source image as the same specific instance — not reinterpreted, not
simplified, not restyled, not substituted by a similar motif.
```

## §2 几何锁（GEOMETRY LOCK · 位置与姿态，防止"标准回望像"）

```
FRAMING   : half-length portrait, 2:3 vertical. The figure occupies the LEFT ~two-thirds of the
            frame; the right third is background. Head crown sits near the top edge; the body is
            cut off at the waist level. No room is added above or below.

HEAD/TURN : face turned toward the viewer's LEFT and tilted slightly DOWN. Only the LEFT eye is
            fully resolved; the right eye is seen at the extreme left edge of the face, mostly
            cropped by the cheek/hair — do NOT symmetrise the face into a straight-on view.
            Chin is slightly tucked; the gaze is soft and directed down-left, not at the camera.

SHOULDER  : the near (viewer-left) shoulder is BARE and pushed forward, so the shoulder line
            slopes down-left and reads as a rounded, exposed shoulder occupying the lower-left.
            The chest/torso turns away from the viewer (over-the-shoulder turn), not frontal.

HAIR MASS : hair falls as a long straight curtain down the LEFT side of the frame, spilling past
            the frame edge. On the RIGHT side of the frame a thick gathered hank of hair drops
            past the shoulder, and a separate strand crosses the chest diagonally.
```

## §3 细节清单（DETAIL INVENTORY · 逐件，顺序即优先级）

```
1) HAIR
   - very long, straight, pale cream-ashy blonde / light ash-grey, LOW saturation, no yellow.
   - long bangs with separated spiky strands; centre-part-ish with strands crossing the brow.
   - soft rendering: broad brushed colour masses, not individual hair threads; matte, no gloss.

2) STAR-STICKER CLUSTER  (viewer-left hair, three visible)
   - small white five-pointed star motifs scattered on the bangs and left-side hair, laid FLAT
     on the hair surface, of DIFFERENT sizes and opacities (one solid, two faint).
   - positions (full-image fractions, verified against a burnt-in ruler):
       small solid star at about (0.27, 0.15);
       faint small star in the mid-bangs at about (0.53, 0.20);
       faint small star at the far left, about (0.00, 0.22) — clipped by the frame edge.

3) BLUE X HAIRPIN  (in the bangs, viewer-right of the visible eye)
   - a small light BLUE "X" / crossed-bar clip spanning about (0.56–0.62 x, 0.26–0.30 y).
   - it sits BELOW the mid-bangs star and clearly LEFT of the flower cluster. Thin, flat,
     blue-grey metal look. Do not move it up toward the crown.

4) FLOWER ORNAMENT  (character's LEFT temple, above the ear → viewer's RIGHT of frame)
   - a CLUSTER of FOUR star-shaped flowers, pale icy lavender-white, semi-translucent matte petals.
   - each flower: 5 pointed petals + a small pale round centre; petals have 1–2 faint creases.
   - arrangement (verified against a burnt-in ruler; the cluster spans roughly 0.50–0.88 x,
     0.13–0.34 y and is NOT a tight rosette — the flowers are spaced apart and overlap pairwise):
       F1 SMALL  upper-left of the group, about (0.53–0.62 x, 0.19–0.26 y)
       F2 LARGE  upper-right, the biggest bloom, about (0.61–0.76 x, 0.16–0.28 y)
       F3 MEDIUM lower-left, its petals reaching the LOWEST point of the cluster,
                 about (0.50–0.64 x, 0.29–0.34 y)
       F4 LARGE  lower-right, about (0.71–0.88 x, 0.20–0.31 y)
   - F3 and F4 carry long slender petals that stick out down-left and down-right respectively;
     these protruding petals are the cluster's most recognisable silhouette feature.
   - the group is attached flat to the side of the head just above and behind the ear.

5) EARRING  (character's LEFT ear → hangs down the viewer-right side, IN FRONT of the hair)
   - hanging FEATHER earring, drawn in detail with visible barbs, hanging VERTICALLY.
   - order top→bottom: a small dark star/cross-shaped metal stud at the lobe (about 0.64–0.67 x,
     0.35–0.39 y); below it the feather begins at about y 0.40 and hangs to about y 0.52,
     i.e. to mid-neck level.
   - the feather is pale white-blue at its base → bright cyan-blue in the middle → deeper blue at
     the tip. It hangs on the bare skin BESIDE the hair, not on top of the hair mass.
   - SPATIAL RELATION THAT MUST BE KEPT: the feather is BELOW and to the LEFT of the flower
     cluster. The flower ornament is above-right of the feather on the head; the feather hangs
     down past the jaw onto the neck. They are two separate objects — never merge them into one,
     and never hang the flower from the earring.

6) NECKLACE, CHOKER AND PENDANTS
   - CHOKER: two tiers forming a wide band across the base of the throat.
       upper tier — a row of white connected star / knot motifs (repeating figure-eight stars);
       lower tier — dense BLACK beadwork (dark floral/cross pattern) with a dotted lace edge.
       tied at the back of the neck with thin black cord, a knot visible at the nape.
   - FINE CHAIN NECKLACE: a thin black beaded chain hanging in a wide catenary loop BELOW the
     choker, crossing the chest and continuing out of frame at the lower-left.
   - PENDANT: a single round-ish bright CYAN-BLUE gem (strongly saturated blue, ~#487890–#4890A8)
     on that thin chain, sitting at about (0.38–0.44 x, 0.60–0.70 y) against the chest.
   - total jewellery count is high — do NOT reduce it to one necklace.

7) SHOULDER-STRAP ORNAMENT
   - on the strap over the near shoulder there is a small SILVER-WHITE pointed star / cross
     ornament with a tiny BLACK teardrop hanging below it.

8) GARMENT
   - white off-shoulder slip dress with a sheer lace overlay.
   - the viewer-left shoulder and upper chest are BARE; no sleeve covers that shoulder.
   - thin white strap over the character's left shoulder (the one with the star ornament).
   - a sheer, semi-transparent panel with scattered white floral / star lace motifs covers the
     chest area, letting the skin read through it; the lace has sprig-shaped flowers.
   - a long white wrist-length sleeve / detached cuff with longitudinal seam lines and soft folds
     runs from the mid-upper arm down out of the lower frame.
   - a soft transparent sash / band crosses the body diagonally over the chest.
   - at the lower-right of the frame sits a DARKER grey-purple band with panel seams
     (the dress bodice / waist section), receding into shade.

9) BACKGROUND
   - muted grey-green / olive-grey and neutral grey, LOW contrast, soft watercolour-like blotches.
   - faint upright structures behind the head (thin diagonal lines, a suggestion of a post or
     window frame at the upper-left), deliberately vague and non-specific.
   - the overall background is desaturated; it must not compete with the character.
```

## §4 禁改清单（PROHIBITION · 防止被风格基准"平均"掉）

```
NEGATIVE / DO NOT INCLUDE:
- Do not add ANY element from the style reference image (its characters, props, costume pieces,
  motifs, colours of its subject, or its background objects).
- Do not change the hair colour to any warm/red/blonde hue; keep it pale ash, low saturation.
- Do not move the flower ornament to the other side of the head, and do not merge it with the
  feather earring.
- Do not replace the choker's black bead tier with a plain ribbon or a single thin chain.
- Do not add the trim to a generic white dress; keep the sheer lace overlay and the seam sleeve.
- Do not symmetrise the face, do not re-centre the figure, do not zoom in on the head.
- Do not remove the thin chain + cyan gem pendant.
- Do not turn the pale, soft rendering into glossy 3D shading.
```

## §5 风格块拼接位置（接在 §4 之后）

风格基准图的 B 段标签 / D 段 prompt 直接紧跟 §4。拼完的段落顺序固定为：

```
§1 IDENTITY BANNER
§2 GEOMETRY LOCK
§3 DETAIL INVENTORY
§4 PROHIBITION
§5 STYLE BLOCK   (来自基准图提取，如 crimson-dominant palette 那一组)
```

风格块里的**色彩方案**要单独处理：基准图的主色若与人物固有色冲突（例如深红主色 vs 灰白人物），
在 §5 之后补一句范围限定：

```
Apply the style's colour scheme to the LIGHTING, SHADOW STRUCTURE and BACKGROUND only.
The character's local colours (pale ash hair, blue eyes, white lace dress, cyan gem) are fixed
and must not be re-graded toward the style's dominant hue.
```

---

## §6 采样色值（供对照，非约束）

按 837×1243 原图降采样聚类所得，**已量化到 24 级箱**，仅作量级参考，不要当成精确取色：

| 部位 | 参考值 | 说明 |
|---|---|---|
| 蓝色系（眼 / 宝石 / 羽毛） | `#487890` `#306078` `#4890A8` | 图内唯一高饱和色 |
| 亮中性（蕾丝裙 / 高光发） | `#F0F0F0` `#C0C0C0` `#D8D8C0` | 偏暖白，非纯白 |
| 发身主体 | `#787878` `#909090` `#787860` | 低饱和灰，微暖 |
| 暗部（颈环珠绣 / 描线） | `#303030` `#181818` | 近黑 |
| 背景 | `#909078` `#484830` `#484848` | 灰绿 / 橄榄灰，低对比 |

## §7 已知不确定项

- 色值为降采样聚类结果，箱宽 24，**非精确取色**；需要钉死色值时应在原图对应区域做单点采样。
- 花朵数量：确认 4 朵（F1–F4），但 F1 与 F2 重叠处可能还藏有一朵，密集区无法完全排除。
- 星形贴饰：确认 3 个，其中 2 个极淡；左下方（0.06, 0.22 附近）还有一处更淡的，不排除更多。
- 肩带小挂饰的黑色下垂件：放大后仍偏小，判为"黑色水滴/菱坠"，不确定是否为宝石。
- 背景上部细线结构：无法判定是树干、栏杆还是窗框，故在 §3 中只写"暗示性的直立结构"。
- 羽毛的精确起止：上端小饰件在 y≈0.35–0.39 区间，羽毛主体 y≈0.40–0.52；由于该处被发丝
  局部遮挡，上缘边界有约 ±0.02 的不确定度。

### 已核实（用 `ruler.py` 烧入坐标网格逐点确认，非目测估算）

- 花簇的整体跨度与四朵各自位置（见 §3 第 4 条）。
- 蓝色 X 发夹在 bangs 中的位置，及其位于花朵**左侧**的关系。
- 耳饰羽毛相对花簇为"**下方偏左**"，二者不相连。
- 星形贴饰三个位置。

### 未能核实

- 背景具体物象（树木 / 栏杆 / 窗框）。
- 花朵内部是否有被遮挡的第五朵。

## 相关文件

- `compose/charsheet/crop.py` — 生成各区域放大图
- `compose/charsheet/ruler.py` — 在指定区域烧入坐标网格（核实位置用）
- `compose/charsheet/palette.py` / `palette2.py` — 色值采样
- `compose/charsheet/c2_head.png` `c3_flower.png` `c4_neck.png` `c5_dress.png` `c6_face_grid.png` `c7_lineart.png` — 放大证据图
- `compose/charsheet/r1_head_ruler.png` `r2_ear_ruler.png` — 带坐标网格的位置证据图
