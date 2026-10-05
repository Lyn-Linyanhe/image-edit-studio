# 三图提示词（角色互换版）· 图1=内容 · 图2=画法/风格 · 图3=姿态

**用图与角色（你在工具里已设定）**

| 编号 | 文件 | 角色 | 提供什么 |
|---|---|---|---|
| **图1** | `43e24ec8…png`（837×1243） | **要改的内容图** | 身份、五官、发型发色、饰品、服装、背景、**全部颜色**、画幅 |
| **图2** | `47ec32ac…jpg`（1200×1600） | **参考图 · 画法/风格** | **只取画法**（笔触、线稿、明暗处理、材质） |
| **图3** | `187dafa4…jpg`（1200×1600） | **参考图 · 姿态** | **只取姿态**（身体朝向、头部角度、视线、双手与书的动作） |

> 图片顺序不变，只是**图2 与图3 的角色对调**。
> 服务端会自动在提示词最前面注入编号说明（`图1 = 要修改的内容图…图2 = 画法 / 风格参考…图3 = 姿态参考…`），
> 与本文件一致。下面的 prompt 也是自包含的，粘到别处也能用。

---

## 0. 互换带来的两点变化（已核对）

**① 画法互换基本无影响**
47EC 与 187D 同属 A 鼠尾草米白分支：笔触密度 3.00 vs 3.06、内容饱和度 0.036 vs 0.035、都是铅笔断线 + 水彩渗染。
→ 风格结果不会因为换参考而变。

**② 姿态互换让风险明显上升（本版最关键的一点）**

| | 图1（现有姿态） | 上一版的姿态参考（47EC） | **本版的姿态参考（图3 = 187D）** |
|---|---|---|---|
| 身体 | 肩线朝远离观者方向转 | 背对观者、侧肩 | 3/4 侧转、肩线倾斜 |
| 头 | **回望观者、略低** | 向画面左侧回转回眸（≈原姿态） | **转向画面右侧并微微上抬**，下巴略高于肩线 |
| 视线 | 朝观者 | 朝画面左侧（≈原姿态） | **落向画面右上、画外，不看观者** |
| 手 / 书 | 画面内**没有手和书** | 一手扣书左上缘、**竖直**抱书 | **双手横抱**一本书（接近水平，10–20° 微倾） |

**上一版之所以保真好**，是因为姿态参考与图1 原姿态几乎相同 → 头部基本不用重画。
**本版要把头转到右上并抬头**，属于头部大角度重绘——**这正是上次丢掉辨识度的机制**（r1 那次的失败原因）。
所以本版所有防线都必须开足，尤其是发色与眼睛。

**③ 另一个必须防的串味（方向反了）**
现在图3 是姿态参考，它那本**横抱**的书**应该跟过来**；
而图2 是画法参考，它那本**竖抱**的书**绝不能跟过来**。两条要分别写清。

**尺寸**：图1 = 0.673（≈2:3）。用 low + 勾选「跟随原图比例」→ 1024×1536。
（注意实测：中转站不严格遵守尺寸，请求 1024×1536 实际返回过 1029×1528，所以比例只是近似。）

---

## 1. PRESERVE（图1 的身份与内容，逐项）

- 同一个年轻女性、同一套五官比例。脸随图3 的姿态转向右上并微抬，**但五官特征完全不变**
- **头发**：长直发，灰亚麻/灰褐带浅黄绿调，约 `#8C8C83`——柔和的暖灰褐，
  **不是白色、不是银灰、不是铂金白**；长刘海；数缕细直发丝横过脸前；长发垂至画面下方
- **发间小物**（随头部一起转，相对头部的位置关系不变）：
  - 发间**左侧** 3–4 枚白色小星形发饰
  - 刘海**右侧**一枚浅蓝色 X 形发夹
- **眼睛**：明亮**高饱和青蓝色**，内有大块白高光；深色眼线、根根分明的长睫毛。**不要褪成灰蓝**
- **小痣**：只有一颗，仍在**同一只眼**（她右眼）下方——头转动后不要换眼、不要消失
- **头饰**：右耳上方至头顶，**3 朵**白色到淡紫的五/六瓣**长尖瓣**花（不是圆瓣），随头转动
- **耳饰**：右耳一枚黑白棋盘格圆片 + 垂下的**长青蓝色羽毛**，随头转动
- **颈饰**：黑白小格棋盘纹缎带（上缘一圈白色雪花蕾丝）+ 细链 + **青蓝凸圆宝石吊坠**
- **服装**：白色半透明蕾丝罩衫，胸前覆白色雪花形与叶片状蕾丝贴花，肩颈裸露。
  下缘裁切下移后，下半身是新区域 → 延续同一件罩衫往下画，**保持露肩无袖，不要加袖子、不要换服装**
- **背景**（保留结构，只简化提亮）：灰绿与橄榄色块面、淡奶白与浅灰几何面、
  右上**大型浅色圆形**、右侧**带斜纹的竖直绳索**、**左亮右暗**的关系。元素位置一律不动
- **颜色**：图1 每个元素自己的颜色全部不变

## 2. POSE（照图3 = 187D 来，已在原图放大核对）

- 3/4 侧身，**肩线倾斜**；**可见耳在画面左侧**
- **头转向画面右侧并微微上抬**，下巴略高于肩线
- **视线落向画面右上、画外**，不与观者对视；表情安静、淡淡的分神、嘴唇轻抿
- **双手横抱一本书**：
  - 一本**合上的硬壳书**，**接近水平**横抱在胸前，只有约 **10–20° 的轻微倾斜**
  - **封面朝观者**，**白色书口在书的左侧**
  - **画面右侧的手**搭在封面右上部分，手指朝左内扣、指节朝观者
  - **画面左侧的手**从下方托住书的**左下角**
  - 两只袖子从下方斜伸上来，**两前臂在胸前交叠**
- **画幅**：下缘裁切下移到**腰与髋之间**，把双臂、双手和整本书都装进画面

## 3. STYLE（照图2 = 47EC 来，只取手法）

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
Three images are attached. Image 1 is the CONTENT AND IDENTITY. Image 2 is the STYLE reference.
Image 3 is the POSE reference. Use only what is listed for each, and nothing else.

IMAGE 1 provides the subject, identity, face, hair, ornaments, garments, background, framing and
ALL COLOURS. Image 2 provides ONLY the rendering technique. Image 3 provides ONLY the figure's
pose. Ignore the subject, characters, hair, clothing, props and colours of images 2 and 3.

PRESERVE from image 1 — this is a transfer of an existing character, not a redesign. Do not
reinterpret, simplify, relocate or restyle any of the following:
- the same young woman and the same facial features. Her face turns toward the upper right to
  follow image 3's pose, but no facial feature may change: keep the same eye shape, the same
  nose, the same mouth, the same face proportions and the same apparent age.
- the same ash-taupe hair with a faint yellow-green cast, around #8C8C83 — a muted warm grey-brown.
  It is NOT white, NOT silver, NOT platinum, NOT grey-blonde. Do not lighten it or turn it silver,
  even though both reference images contain silver-haired characters.
- the same straight hair, not wavy and not curly; long bangs; several thin straight loose strands
  crossing in front of the face; hair falling past the bottom of the frame
- the white star-shaped hair ornaments scattered in the hair on the left side of the frame
- the single light blue X-shaped hair clip in the bangs on the right side
- the same bright, strongly saturated cyan-blue eyes with large white highlights, dark eyeliner and
  long distinctly separated eyelashes. Keep the eyes VIVID. Do not desaturate them into grey-blue
  and do not change their hue.
- exactly one small beauty mark, under the SAME eye as in image 1. Keep it under that same eye even
  though the head is now turned the other way; do not move it to the other eye and do not remove it.
- the same three long-pointed lily-like flowers, white to pale lilac, above the right ear. Exactly
  three, petals long and pointed, not round. They rotate with the head.
- the same right-ear earring: a black-and-white checkerboard disc with a long cyan-blue feather
  hanging beneath it on a fine chain; it rotates with the head.
- the same choker: a black-and-white fine checkerboard ribbon trimmed with a row of white
  snowflake-and-star lace, plus a fine chain and a round cabochon cyan gemstone pendant
- the same sheer white translucent lace bodice covered with white snowflake-shaped and
  leaf-shaped lace appliqué. Continue the SAME garment downward over the newly visible lower torso;
  keep it off-shoulder and sleeveless. Do NOT add sleeves and do NOT substitute another garment.
- the same background structure at exactly the same place: soft grey-green and olive planar shapes
  with pale cream and grey facets, the large pale circular disc shape at the upper right, the
  vertical braided cord with diagonal hatching running down the right side, and the same
  left-brighter / right-darker asymmetry. No background element may be moved, replaced, deleted or
  recoloured; only simplify its detail and lift its values so nothing goes dark.

POSE — take this from image 3:
a three-quarter turned body with a slanted shoulder line, seen so that the visible ear is on the
LEFT side of the frame; the head is turned toward the RIGHT side of the frame and tilted slightly
UP, with the chin a little above the shoulder line; the gaze falls toward the upper right and
off-screen, not looking at the viewer; quiet, slightly distracted expression with softly closed
lips. Both hands are in frame, in front of the chest, holding one closed hardcover book: the book
is held across the chest almost horizontally with only a slight tilt of about 10 to 20 degrees, its
cover facing the viewer and its white page block along the LEFT edge; the hand on the right side of
the frame rests on the upper right part of the cover with the fingers curling inward toward the
left and the knuckles facing the viewer, and the hand on the left side of the frame supports the
book from beneath at its lower-left corner; both sleeves come up from below and the forearms cross
in front of the torso. Show the arms, both hands and the whole book completely — extend the bottom
crop down to between the waist and the hip so that the hands and the whole book fit inside the frame.

THE BOOK — the book does not exist in image 1, so give it a colour taken from image 1's own
palette: a muted grey-olive cover in the same warm grey-olive family as image 1's background and
clothing tones. Take its GESTURE (horizontal, both hands) from image 3. Do NOT copy the book or the
book gesture of image 2 — image 2's book is held vertically with one hand at its top edge and that
orientation must not appear.

COLOUR IDENTITY LOCK — image 1 keeps its own colours. Never adopt any hue, colour or palette from
image 2 or image 3. Do not recolour, do not swap palettes, do not shift anything toward
grey-violet, sage green or lavender. Shadows and highlights must be derived from each element's
OWN colour — not replaced by any fixed grey, violet or blue.

STYLE — take this from image 2, technique only, no palette:
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
around 0.40 to 0.55, and keep the overall tonal range spread across roughly 0.45 so the light, mid
and shadow steps remain readable. Do not flatten everything into near-white.

MOOD: quiet, gentle, introspective, wistful and literary. Airy and light, never heavy or dark.

DO NOT TAKE FROM IMAGE 2 (style only): its silver-grey hair colour, its over-the-shoulder
look-back head angle, its vertically held book and its one-hand grip on the book's top edge, its
sage green ribbon bow, its knitwear, its facial features, its plain white background, its 3:4
aspect ratio.

DO NOT TAKE FROM IMAGE 3 (pose only): its silver-grey hair colour, its sage green ribbon bow, its
cream turtleneck and sage cardigan, the dark sage green cover of its book, its facial features, its
plain white background, its 3:4 aspect ratio and its author signature.

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
随附三张图。图1 是内容与身份；图2 是画法参考；图3 是姿态参考。
三张图各取各的，不要越界。

图1 提供主体、身份、五官、发型、饰品、服装、背景、画幅和全部颜色。
图2 只提供画法。图3 只提供人物姿态。
图2、图3 里的人物、头发、服装、道具和所有颜色一律不要。

保持图1 不变（这是对已有角色的迁移，不是重新设计；不要重新诠释、简化、挪动或改变任何一项）：
同一个年轻女性、同一套五官。脸随图3 的姿态转向右上并微抬，但五官特征完全不变——
同样的眼型、鼻形、嘴形、面部比例和年龄感；
同一头长直灰亚麻色（带浅黄绿调，约 #8C8C83）头发——柔和的暖灰褐，
不是白色、不是银灰、不是铂金白。不要提亮它、不要变成银灰
（注意：两张参考图里都是银灰发角色，这里尤其不能跟）；
同一头直发，不是波浪不是卷发；长刘海；数缕细直发丝横过脸前；长发垂到画面下方；
画面左侧发间散布的白色星形发饰；
刘海右侧那一枚浅蓝色 X 形发夹；
同一双明亮的、饱和度高的青蓝色眼睛（带大块白高光）、深色眼线、根根分明的长睫毛——
眼睛要保持鲜艳，不要褪成灰蓝，不要改变色相；
只有一颗小痣，位于与图1 同一只眼睛的下方——头转了方向也要保持在原来那只眼下，
不要换到另一只眼，也不要去掉；
右耳上方那三朵白色到淡紫的五/六瓣长尖瓣花，一共三朵，花瓣长而尖，随头部一起转；
右耳那枚黑白棋盘格圆片 + 垂下的长青蓝色羽毛耳饰，随头部一起转；
颈部那条黑白小格棋盘纹缎带（上缘一圈白色雪花蕾丝）+ 细链 + 青蓝凸圆宝石吊坠；
那件白色半透明蕾丝罩衫，胸前覆白色雪花形与叶片状蕾丝贴花；
下缘裁切下移后露出的下半身要延续同一件罩衫往下画，
保持露肩无袖——不要加袖子，不要换成别的服装；
背景结构与元素位置完全照旧：灰绿与橄榄色块面、淡奶白与浅灰几何面、右上那枚大型浅色圆形、
右侧那根带斜纹的竖直绳索，以及左亮右暗的关系。
背景里任何元素都不许挪动、替换、删除或改色，只简化细节、提亮明度，不让任何区域变暗。

姿态（照图3 来）：
身体侧转约四分之三，肩线倾斜，可见的耳朵在画面左侧；
头转向画面右侧并微微上抬，下巴略高于肩线；
视线落向画面右上、画外，不看观者；表情安静、淡淡的分神，嘴唇轻抿。
双手都在画面内、抱在胸前，横抱着一本合上的硬壳书：
书接近水平横放，只有约 10 到 20 度的轻微倾斜，封面朝观者，白色书口在书的左侧；
画面右侧的手搭在封面右上部分、手指朝左内扣、指节朝观者，
画面左侧的手从下方托住书的左下角；两只袖子从下方伸上来，两前臂在胸前交叠。
要把双臂、双手和整本书都完整画进画面——下缘裁切下移到腰与髋之间，别把手和书裁掉。

那本书：图1 里原本没有书，所以颜色要从图1 自己的配色里取——
用与图1 背景和衣物同族的柔和暖灰橄榄色封面。
书的抱持方式照图3（横抱、双手）；
不要照搬图2 的书，也不要它的抱法——图2 那本书是竖着、一只手扣在上缘的，那个方向绝不能出现。

颜色规则：图1 每个元素自己的颜色一律保持，绝不采用图2、图3 的任何色相或配色。
不要换色、不要调色板替换、不要往灰紫或鼠尾草绿上靠。
暗部与高光从每个元素自己的色相派生，不要统一换成灰或蓝。

画法（照图2 来，只取手法）：
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

不要从图2 搬（它只给画法）：它的银灰色头发、它"侧身回眸"的头部角度、
它那本竖着抱的书和"一只手扣书的上缘"的握法、它的墨绿色缎带蝴蝶结、它的针织衣物、
它的五官、它的纯白背景、它的 3:4 画幅。

不要从图3 搬（它只给姿态）：它的银灰色头发、它的墨绿色缎带蝴蝶结、
它的米白高领针织与鼠尾草绿开衫、它那本书的墨绿封面、它的五官、
它的纯白背景、它的 3:4 画幅、它的署名水印。

不要：3D 渲染、厚涂、赛璐璐平涂、干净闭合的矢量线稿、黑色轮廓线、深阴影、暗背景、
过曝发白的扁平画面、高饱和荧光色、换色、调色板替换、往灰紫或鼠尾草绿偏色、
白色或银灰或铂金发色、褪成灰蓝的眼睛、改成黑白或全灰、光斑粒子、颗粒纹理、水印签名文字。
```

---

## 6. 参数与验收

**参数**
| 项 | 建议 |
|---|---|
| 上传 | 图1 放「要改的图」；图2、图3 按原顺序加进「参考图」——**先 47ec32ac 后 187dafa4** |
| 角色 | 图2 → **画法 / 风格**；图3 → **姿态** |
| 修改范围 | **整张图**（编号正好 图1/图2/图3；遮罩模式会挤掉 图2） |
| 画质 / 尺寸 | low + **勾选「跟随原图比例」** → 1024×1536（2:3）。要 2K 只能选 2048×2048（1:1，会补白边） |
| 适配 | 补白边（pad） |
| 张数 | **建议出 4 张选优**——本版要重画头部并新增双手与书，是难度最高的一版 |
| 色相兜底 | 出图后跑 `preserve_hue.py --sat-scale 1.0 --chroma-blur 6`（几何位移较大，模糊半径给足） |

**验收（逐项对图）**
- [ ] 发色**没变银灰**（仍是灰亚麻带黄绿）——**本版最高风险**
- [ ] 眼睛仍是**高饱和青蓝**，不是灰蓝
- [ ] **只有一颗**小痣，且在**同一只眼**下方（头转了方向最容易出错的一项）
- [ ] 五官没被"重画成另一个人"：眼型、脸型、年龄感与图1 一致
- [ ] **3 朵**长尖瓣花在右侧耳上方；白色星形发饰在左侧；蓝 X 发夹在刘海右侧
- [ ] 棋盘格颈饰 + 雪花蕾丝 + 青蓝宝石吊坠 / 棋盘格耳饰 + 蓝羽毛 都在
- [ ] 姿态是"头朝右上微抬 + **横抱**书、双手在书上"
- [ ] 书是**横**的（10–20° 微倾），**不是**图2 那种竖抱
- [ ] 书封面取自图1 的暖灰橄榄，不是墨绿
- [ ] **没有袖子**，罩衫延续一致
- [ ] 手指数量正常
- [ ] 背景元素位置未动、左亮右暗
- [ ] 无黑，但也**没有过曝发白**

---

## 7. 风险（按严重度）

1. **头部大角度重绘 → 身份漂移（本版最高风险）**：
   本版要求把头从"回望观者、略低"改成"朝右上、微抬、视线画外"，属于**整颗头重画**。
   上一次丢掉辨识度正是这个机制（发色被漂白、眼睛褪成灰蓝、花与星饰丢失）。
   → 防线：PRESERVE 里逐项写死 + `COLOUR IDENTITY LOCK` + 出图后 `preserve_hue.py`。
   → **若结果仍漂移，最有效的办法是改用「局部重绘」：把头部与头饰整块排除出重绘区**，
   只让身体按图3 的姿态重画。但那会拿不到"头朝右上"的效果——这是本版的根本取舍。
2. **银灰发漂移**：图2、图3 都是银灰浅发，图1 也是浅发——三方先验重合。已在三处点名拦截。
3. **两本书的抱法串味**：图2 是竖抱（一只手扣上缘），图3 是横抱（双手）。
   本版要的是**图3 的横抱**；prompt 里两个方向都写了拦截句。出图后重点看书的**朝向**。
4. **小痣换眼**：头转向改变后，模型很容易把痣画到另一只眼下或画成多个。已在 PRESERVE 里单独点名。
5. **明暗抬过头**：曾出现过过曝（P05 0.693，超出风格上限 0.616）。prompt 已给数值区间，出图后机检。
6. **手指崩坏**：双手与书都是新增内容。建议出 4 张选优，优先挑手画得对的。
