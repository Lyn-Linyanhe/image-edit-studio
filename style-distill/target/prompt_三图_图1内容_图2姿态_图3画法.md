# 三图提示词 · 图1=内容/身份 · 图2=姿态 · 图3=画法/风格

**用图与角色（你在工具里已设定）**

| 编号 | 文件 | 角色 | 提供什么 |
|---|---|---|---|
| **图1** | `43e24ec8…png`（837×1243） | **要改的内容图** | 身份、五官、发型发色、饰品、服装、背景、**全部颜色**、画幅 |
| **图2** | `47ec32ac…jpg`（1200×1600） | **参考图 · 姿态** | **只取人物姿态**（身体朝向、头部角度、视线、手与书的动作） |
| **图3** | `187dafa4…jpg`（1200×1600） | **参考图 · 画法/风格** | **只取画法**（笔触、线稿、明暗处理、材质）；不取内容、姿态、道具、配色 |

> 在工具里运行时，服务端会自动在提示词最前面注入一段编号说明（`图1 = 要修改的内容图…图2 = 姿态参考…图3 = 画法 / 风格参考…`），
> 与本文件的分工一致。下面的 prompt 本身也是自包含的，直接粘到别处也能用。

---

## 0. 关键前提（已核对）

**图2 的姿态与图1 原本的姿态高度接近**——两者都是"侧身 + 回眸"：

| | 图1（现有） | 图2（姿态参考） |
|---|---|---|
| 身体 | 肩线朝远离观者方向转 | 背对观者，看到背部与侧肩 |
| 头 | 回望、略低 | 向**画面左侧**回转回眸，接近平视 |
| 可见耳 | — | 在**画面右侧** |
| 手 / 书 | **画面里没有手和书** | 一手扣住书的**左上缘**，另一手在书下部握持；**书竖直**抱在胸前偏左，封面朝观者，白色书口在书**左侧**；米白针织袖口 |

**推论**：这次姿态迁移的实际改动很小（头部再转一点 + 新增手与书）。
→ **身份保真风险远低于上一版**（上一版要求"头朝画面右上微仰"，是大幅改造）。

**一个必须防的串味**：图3 里也有一本书，而且是**横抱在胸前**的（双手抱书）。
图3 只提供画法，所以**它那本横抱的书绝不能跟过来**——书只能来自图2 的**竖直**抱持。prompt 里有专门一句拦这个。

**尺寸**：图1 = 0.673（≈2:3）→ 勾选「跟随原图比例」会在 low 档自动选 **1024×1536**（误差 0.007）。
图2/图3 是 0.75（3:4），会被补白边到请求尺寸；对"只取姿态/只取画法"的参考没有影响。

---

## 1. PRESERVE（图1 的身份与内容，逐项）

- 同一个年轻女性、同一套五官比例。脸随图2 的姿态略作回转，**但五官特征完全不变**
- **头发**：长直发，灰亚麻/灰褐带浅黄绿调，实测约 `#8C8C83`——是柔和的暖灰褐，
  **不是白色、不是银灰、不是铂金白**；长刘海；数缕细直发丝横过脸前；长发垂至画面下方
- **发间小物**（随头部一起转，相对头部的位置关系不变）：
  - 发间**左侧** 3–4 枚白色小星形发饰
  - 刘海**右侧**一枚浅蓝色 X 形发夹
- **眼睛**：明亮的**高饱和青蓝色**，内有大块白高光；深色眼线、根根分明的长睫毛
- **小痣**：只有一颗，仍在**同一只眼**（她右眼）下方
- **头饰**：右耳上方至头顶，**3 朵**白色到淡紫的五/六瓣**长尖瓣**花（不是圆瓣）
- **耳饰**：右耳一枚黑白棋盘格圆片 + 垂下的**长青蓝色羽毛**
- **颈饰**：黑白小格棋盘纹缎带（上缘一圈白色雪花蕾丝）+ 细链 + **青蓝凸圆宝石吊坠**
- **服装**：白色半透明蕾丝罩衫，胸前覆白色雪花形与叶片状蕾丝贴花，肩颈裸露
- **背景**（保留结构，只简化提亮）：灰绿与橄榄色块面、淡奶白与浅灰几何面、
  右上**大型浅色圆形**、右侧**带斜纹的竖直绳索**、**左亮右暗**的关系
- **颜色**：图1 每个元素自己的颜色全部不变

## 2. POSE（照图2 来）

- 身体**背对观者**（主要看到背部与侧肩），肩线倾斜
- 头向**画面左侧**回转**回眸**，接近平视，视线朝向画面左侧（朝观者方向）
- 可见耳在**画面右侧**；表情安静，嘴唇轻抿
- **手与书**：一只手从上方扣住书的**左上缘**、手指扣在书口上；另一只手在书的**下部**握持；
  一本**合上的硬壳书**以**竖直**方向抱在胸前偏左，**封面朝观者**，白色书口在书的**左侧**；
  袖口是米白色针织
- **画幅**：需要看到手与书 → 下缘裁切比图1 略低一点（图1 裁在胸口，装不下手和书）

## 3. STYLE（照图3 来，只取手法）

- 水彩 + 彩铅手绘质感的日系动漫插画
- **铅笔草稿线**：断续、粗细变化、收笔出锋、叠线重描、轮廓不闭合
- **上色**：极淡水彩洗笔，边界模糊渗染、轻微溢出线外，保留扫笔擦痕
- **高光**：把该元素**自身色相**提亮，不靠加白
- **光影**：正面偏上方柔和散射光；无投影、无硬边阴影、无轮廓光、无光晕
- **明暗**：压成三档；**无黑**，最暗处抬到中等明度
- **色彩处理**：饱和度压到约 0.08（很低）；明度抬高；对比压低
- **边缘**：柔，不锐利、不塑料光泽；无噪点、无颗粒、无画布纹理
- **背景**：只简化细节与提亮，元素位置一律不动

---

## 4. 完整提示词 · 英文版

```
Three images are attached. Image 1 is the CONTENT AND IDENTITY. Image 2 is the POSE reference.
Image 3 is the STYLE reference. Use only what is listed for each, and nothing else.

IMAGE 1 provides the subject, identity, face, hair, ornaments, garments, background, framing and
ALL COLOURS. Image 2 provides ONLY the figure's pose. Image 3 provides ONLY the rendering
technique. Ignore the subject, characters, hair, clothing, props and colours of images 2 and 3.

PRESERVE from image 1 — this is a transfer of an existing character, not a redesign. Do not
reinterpret, simplify, relocate or restyle any of the following:
- the same young woman and the same facial features; her face turns slightly to follow image 2's
  pose, but every facial feature stays identical
- the same ash-taupe hair with a faint yellow-green cast, around #8C8C83 — a muted warm grey-brown.
  It is NOT white, NOT silver, NOT platinum, NOT grey-blonde. Do not lighten it or turn it silver,
  even though both reference images contain silver-haired characters.
- the same straight hair, not wavy and not curly; long bangs; several thin straight loose strands
  crossing in front of the face; hair falling past the bottom of the frame
- the white star-shaped hair ornaments scattered in the hair on the left side of the frame
- the single light blue X-shaped hair clip in the bangs on the right side
- the same bright, strongly saturated cyan-blue eyes with large white highlights, dark eyeliner and
  long distinctly separated eyelashes. Keep the eyes VIVID, not desaturated grey-blue.
- exactly one small beauty mark, under the same eye as in image 1
- the same three long-pointed lily-like flowers, white to pale lilac, above the right ear. Exactly
  three, petals long and pointed, not round.
- the same right-ear earring: a black-and-white checkerboard disc with a long cyan-blue feather
  hanging beneath it on a fine chain
- the same choker: a black-and-white fine checkerboard ribbon trimmed with a row of white
  snowflake-and-star lace, plus a fine chain and a round cabochon cyan gemstone pendant
- the same sheer white translucent lace bodice covered with white snowflake-shaped and
  leaf-shaped lace appliqué, bare shoulders and neck
- the same background structure at exactly the same place: soft grey-green and olive planar shapes
  with pale cream and grey facets, the large pale circular disc shape at the upper right, the
  vertical braided cord with diagonal hatching running down the right side, and the same
  left-brighter / right-darker asymmetry. No background element may be moved, replaced, deleted or
  recoloured; only simplify its detail and lift its values so nothing goes dark.

POSE — take this from image 2:
the body is turned away from the viewer so that mostly the back and the side of the shoulder are
seen, with a slanted shoulder line; the head is turned back over the shoulder toward the LEFT side
of the frame, close to level; the gaze goes toward the left side of the frame, roughly level; the
visible ear is on the RIGHT side of the frame; quiet expression with softly closed lips.
Both hands hold one closed hardcover book: one hand comes from above and grips the TOP-LEFT edge
of the book with the fingers curling over the page edge, and the other hand holds the book lower
down; the book is held VERTICALLY against the chest, slightly to the left, with its cover facing
the viewer and its white page block along the LEFT edge; the visible cuff is a cream-white knit.
Show the arms, both hands and the whole book inside the frame — extend the bottom crop a little
lower than image 1's crop so that the hands and the book fit.

THE BOOK — the book does not exist in image 1, so give it a colour taken from image 1's own
palette: a muted grey-olive cover in the same warm grey-olive family as image 1's background and
clothing tones. Do NOT copy the book from image 2 and do NOT copy the book from image 3.

COLOUR IDENTITY LOCK — image 1 keeps its own colours. Never adopt any hue, colour or palette from
image 2 or image 3. Do not recolour, do not swap palettes, do not shift anything toward
grey-violet, sage green or lavender. Shadows and highlights must be derived from each element's
OWN colour — not replaced by any fixed grey, violet or blue.

STYLE — take this from image 3, technique only, no palette:
Redraw in the medium of a japanese anime illustration rendered in traditional watercolor and
colored pencil. Add soft delicate pencil sketch lineart: broken and intermittent contours with
varied line weight, tapered stroke ends and overlapping resketch strokes; contours stay slightly
open and unfinished. Colouring becomes a faint watercolor wash with soft bleeding edges that
slightly overflow the lineart, plus visible brush sweep marks; highlights are made by lightening
each element's own hue rather than by adding white. Lighting flattens to a soft diffuse light from
the front and slightly above: no cast shadows, no hard shadow edges, no rim light, no bloom.
Compress the tonal range to roughly three flat steps. Keep the existing low saturation roughly as
it is — do not reduce it further and do not increase it. Edges stay soft; no grain, no film
texture, no canvas texture.

TONE — high-key but NOT washed out:
There must be NO black anywhere, and lift the deepest tones to mid-value. But do not blow the image
out: keep the content-area mean brightness around 0.72 to 0.78, keep the 5th-percentile brightness
around 0.40 to 0.55, and keep the overall tonal range spread across roughly 0.45 so the light,
mid and shadow steps remain readable. Do not flatten everything into near-white.

MOOD: quiet, gentle, introspective, wistful and literary. Airy and light, never heavy or dark.

DO NOT TAKE FROM IMAGE 2: its silver-grey hair colour, its sage green ribbon bow, its knit
turtleneck and cardigan, its own book and its own garments, its facial features, its plain white
background, its 3:4 aspect ratio.

DO NOT TAKE FROM IMAGE 3: its silver-grey hair colour, and above all its book — image 3's book is
held HORIZONTALLY across the chest with both hands; that pose and that book must NOT appear. Also
do not take its ribbon bow, its knitwear, its facial features, its plain white background, its 3:4
aspect ratio or its author signature.

DO NOT INCLUDE: 3D rendering, CGI, thick impasto oil painting, cel shading, flat hard-edged colour
blocks, clean closed vector linework, black outlines, deep or dramatic shadows, dark background,
washed-out overexposed flat image, saturated or neon colours, hue shift, recolouring, palette swap,
colour cast toward grey-violet or sage green, white or silver or platinum hair, pale desaturated
grey-blue eyes, monochrome conversion, full greyscale, bokeh, sparkles, particles, paper or film
grain, watermark, signature, text.
```

---

## 5. 完整提示词 · 中文版

```
随附三张图。图1 是内容与身份；图2 是姿态参考；图3 是画法参考。
三张图各取各的，不要越界。

图1 提供主体、身份、五官、发型、饰品、服装、背景、画幅和全部颜色。
图2 只提供人物姿态。图3 只提供画法。
图2、图3 里的人物、头发、服装、道具和所有颜色一律不要。

保持图1 不变（这是对已有角色的迁移，不是重新设计；不要重新诠释、简化、挪动或改变任何一项）：
同一个年轻女性、同一套五官；脸随图2 的姿态略作回转，但五官特征完全不变；
同一头长直灰亚麻色（带浅黄绿调，约 #8C8C83）头发——柔和的暖灰褐，
不是白色、不是银灰、不是铂金白。不要提亮它、不要变成银灰
（注意：两张参考图里都是银灰发角色，这里尤其不能跟）；
同一头直发，不是波浪不是卷发；长刘海；数缕细直发丝横过脸前；长发垂到画面下方；
画面左侧发间散布的白色星形发饰；
刘海右侧那一枚浅蓝色 X 形发夹；
同一双明亮的、饱和度高的青蓝色眼睛（带大块白高光）、深色眼线、根根分明的长睫毛——不要褪成灰蓝；
只有一颗小痣，位于与图1 同一只眼睛的下方；
右耳上方那三朵白色到淡紫的五/六瓣长尖瓣花，一共三朵，花瓣长而尖；
右耳那枚黑白棋盘格圆片 + 垂下的长青蓝色羽毛耳饰；
颈部那条黑白小格棋盘纹缎带（上缘一圈白色雪花蕾丝）+ 细链 + 青蓝凸圆宝石吊坠；
那件白色半透明蕾丝罩衫，胸前覆白色雪花形与叶片状蕾丝贴花，肩颈裸露；
背景结构与元素位置完全照旧：灰绿与橄榄色块面、淡奶白与浅灰几何面、右上那枚大型浅色圆形、
右侧那根带斜纹的竖直绳索，以及左亮右暗的关系。
背景里任何元素都不许挪动、替换、删除或改色，只简化细节、提亮明度，不让任何区域变暗。

姿态（照图2 来）：
身体背对观者（主要看到背部与侧肩），肩线倾斜；
头向画面左侧回转回眸，接近平视；视线朝向画面左侧（朝观者方向），大致水平；
可见耳在画面右侧；表情安静，嘴唇轻抿。
双手握着一本合上的硬壳书：一只手从上方扣住书的左上缘、手指扣在书口上，
另一只手在书的下部握持；书本以竖直方向抱在胸前偏左，封面朝观者，白色书口在书的左侧；
可见的袖口是米白色针织。
要把双臂、双手和整本书都装进画面——下缘裁切比图1 略低一点，别把手和书裁掉。

那本书：图1 里原本没有书，所以颜色要从图1 自己的配色里取——
用与图1 背景和衣物同族的柔和暖灰橄榄色封面。
不要照搬图2 的书，也不要照搬图3 的书。

颜色规则：图1 每个元素自己的颜色一律保持，绝不采用图2、图3 的任何色相或配色。
不要换色、不要调色板替换、不要往灰紫或鼠尾草绿上靠。
暗部与高光从每个元素自己的色相派生，不要统一换成灰或蓝。

画法（照图3 来，只取手法）：
改造成水彩与彩铅手绘质感的日系动漫插画。加上柔和的铅笔草稿线——
断续、粗细变化、收笔出锋、叠线重描，轮廓不必闭合。
上色改成极淡的水彩洗笔，边界模糊渗染、允许轻微溢出线外，保留扫笔擦痕；
高光靠把该元素自身色相提亮来表现，不要靠加白。
光改成正面偏上方的柔和散射光：去掉投影、硬边阴影、轮廓光与光晕。
明暗压成三档。饱和度保持现在的低水平，不要再降也不要升。
边缘保持柔；无噪点、无颗粒、无画布纹理。

明暗——要高调，但不要过曝发白：
画面里不要有黑色，把最暗处抬到中等明度。但不要把画面冲成一片白：
内容区域明度均值保持 0.72 到 0.78，第五百分位亮度保持 0.40 到 0.55，
整体明暗跨度保持 0.45 左右，让亮、中、暗三档仍然可读。

氛围安静、温柔、内敛、带书卷气，通透轻盈，不要沉闷发暗。

不要从图2 搬：它的银灰色头发、墨绿色缎带蝴蝶结、针织高领与开衫、它自己的书与服装、
它的五官、它的纯白背景、它的 3:4 画幅。

不要从图3 搬：它的银灰色头发；尤其是它的书——图3 那本书是双手横抱在胸前的，
那个姿态和那本书绝不能出现。也不要它的缎带蝴蝶结、针织衣物、五官、纯白背景、3:4 画幅、署名水印。

不要：3D 渲染、厚涂、赛璐璐平涂、干净闭合的矢量线稿、黑色轮廓线、深阴影、暗背景、
过曝发白的扁平画面、高饱和荧光色、换色、调色板替换、往灰紫或鼠尾草绿偏色、
白色或银灰或铂金发色、褪成灰蓝的眼睛、改成黑白或全灰、光斑粒子、颗粒纹理、水印签名文字。
```

---

## 6. 出图参数与验收

**参数**
| 项 | 建议 |
|---|---|
| 上传 | 图1 放「要改的图」；图2、图3 按此顺序加进「参考图」，角色分别设 **姿态** 与 **画法/风格** |
| 修改范围 | **整张图**（这样编号正好是 图1/图2/图3；用遮罩模式会让红色标记图挤掉 图2） |
| 画质 / 尺寸 | low + **勾选「跟随原图比例」** → 自动 1024×1536（2:3，误差 0.007） |
| 适配 | 补白边（pad） |
| 张数 | 建议出 4 张选优（要新增手与书，手最容易崩） |
| 色相兜底 | 出图后可选跑 `preserve_hue.py --sat-scale 1.0 --chroma-blur 4` |

**验收（逐项对图）**
- [ ] 发色**没有变银灰**（仍是灰亚麻带黄绿）——本次最高风险
- [ ] 眼睛仍是**高饱和青蓝**，不是灰蓝
- [ ] 只有**一颗**小痣，且在同一只眼下方
- [ ] **3 朵**长尖瓣花在画面右侧耳上方；白色星形发饰在左侧；蓝 X 发夹在刘海右侧
- [ ] 棋盘格颈饰 + 雪花蕾丝 + 青蓝宝石吊坠在
- [ ] 棋盘格耳饰 + 蓝羽毛在
- [ ] 姿态是"侧身回眸 + 手竖直抱书"，**不是**图3 那种"双手横抱书"
- [ ] 书是**竖直**的，且颜色取自图1 的暖灰橄榄（不是图2/图3 的墨绿）
- [ ] 手指数量正常
- [ ] 背景元素位置未动，仍左亮右暗
- [ ] 无黑、无暗块，但也**没有过曝发白**

---

## 7. 风险（按严重度）

1. **银灰发漂移（最高）**：图2、图3 **都是银灰浅发**，图1 也是浅发——三方先验重合，
   模型很容易把发色推向银灰。prompt 里三重防线：`PRESERVE` 点名 + `COLOUR IDENTITY LOCK`
   + `DO NOT TAKE FROM IMAGE 2/3` 里各写一次"不要银灰发"。出图后建议跑 `preserve_hue.py`。
2. **图3 的横抱书串味**：图3 里那本书又大又显眼（双手横抱在胸前），而它只应提供画法。
   已用专门段落拦它；出图后重点看书的**朝向**是不是竖直。
3. **手部崩坏**：图1 原本没有手和书，这是新增内容。建议出 4 张选优。
4. **姿态改动很小**，所以头部区域基本不用重画——这是这次保真度好于上一版的原因，
   但也意味着**如果你希望头部转得更侧（严格照图2），需要额外说一句**，否则模型可能就按图1 原来的角度画。
5. **明暗抬过头**：上一版出图出现过过曝（P05 0.693，超出风格上限 0.616）。
   这次 prompt 里已给出数值区间（均值 0.72–0.78 / P05 0.40–0.55 / 跨度 ~0.45），出图后请机检。
