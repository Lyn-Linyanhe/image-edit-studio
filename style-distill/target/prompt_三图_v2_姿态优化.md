# 提示词 v2 · 姿态参考优化版（图1=内容 · 图2=画法 · 图3=姿态）

本版**只优化"姿态"这一段**的写法，角色分工与用图不变。

---

## 0. 为什么要改（诊断）

### 问题 ① 提示词里"不许改"压倒了"要改"

英文版全文约 1300 词，其中讲"保持 / 不要改"的约 **1050 词（80%）**，
讲"姿态要变成什么"的只有约 **250 词**。模型面对内容图（图1）时会**默认继承它的姿态**，
于是"别改"的信号有 20 条、"改"的信号只有 1 条——姿态必然弱。

### 问题 ② 从没说过"图1 自己的姿态要放弃"

这是最关键的缺失。图1 本身是"**回望观者、头微低**"，
而原提示词只说"照图3 取姿态"，**没有声明图1 自己的姿态要被推翻**。
模型在别处又被反复要求"保持图1 不变"，于是有充分理由保留原姿态。

### 问题 ③ 姿态写成了一整段长句

头部角度、视线、身体朝向、两只手、书的朝向、裁切全挤在一个约 200 词的段落里。
模型通常只跟住前几个从句，后面丢掉。

## 0.1 本版的四条改法

| 改法 | 具体做法 |
|---|---|
| **① 把"要改什么"提到最前面** | 新增 `THE ONLY THINGS THAT CHANGE` 段，紧跟角色声明，在 1000 多字的"保持"之前 |
| **② 明确推翻图1 的原姿态** | 写成 **before → after** 对照，并加一句**自检判据**：若成图里她仍在看观者或头仍低着，则姿态没生效 |
| **③ 姿态拆成编号 + 排优先级** | 4 条编号，并声明**重要性顺序**：头部与视线 > 身体与肩 > 手与书 > 裁切。告诉模型可以牺牲什么、不能牺牲什么 |
| **④ 把"原姿态"写进负向** | 负向里加入 `head lowered` / `looking at the viewer` / `eye contact with the camera` / `the same pose as image 1` |

---

## 1. 完整提示词 · 英文版（v2）

```
Three images are attached. Image 1 is the CONTENT AND IDENTITY. Image 2 is the STYLE reference.
Image 3 is the POSE reference. Use only what is listed for each, and nothing else.

THE ONLY THINGS THAT CHANGE — the whole rest of the picture stays exactly as image 1:
1) The POSE of the figure. Image 1's own pose must be REPLACED, not kept.
   - what image 1 shows now: the head looking back toward the viewer, the head slightly lowered,
     no hands visible in frame
   - what the result must show instead: the head turned toward the RIGHT side of the frame and
     tilted slightly UP, the gaze going to the upper right and off-screen, NOT looking at the
     viewer; both hands visible, holding one closed book in front of the chest
   - SELF-CHECK: if the finished picture still shows the head looking at the viewer, or the head
     still lowered, or no hands, then the pose was NOT applied. Fix it before finishing.
2) A closed hardcover book held by both hands, which does not exist in image 1 at all.
Everything else — the face and its features, the hair, every ornament, the garment, the
background, and every colour — is preserved from image 1 exactly as described further below.

POSE — copy these from image 3. Apply them in this order of importance, so that if you cannot
satisfy everything, the earlier items are kept and the later ones give way:
1. HEAD AND GAZE (most important): the head is turned toward the RIGHT side of the frame and
   tilted slightly UP, with the chin a little above the shoulder line; the gaze falls toward the
   upper right and off-screen; the eyes do not meet the viewer. Expression quiet and slightly
   distracted, lips softly closed.
2. BODY AND SHOULDERS: a three-quarter turned body with a slanted shoulder line, seen so that the
   visible ear is on the LEFT side of the frame.
3. HANDS AND BOOK: both forearms come up from below and cross in front of the torso. One closed
   hardcover book is held ACROSS the chest almost horizontally, with only a slight tilt of about
   10 to 20 degrees; its cover faces the viewer and its white page block runs along the LEFT edge.
   The hand on the right side of the frame rests on the upper right part of the cover with the
   fingers curling inward toward the left and the knuckles facing the viewer. The hand on the left
   side of the frame supports the book from beneath at its lower-left corner.
4. CROP (least important): extend the bottom crop down to between the waist and the hip so that
   the arms, both hands and the whole book fit inside the frame.

PRESERVE from image 1 — this is a transfer of an existing character, not a redesign. Do not
reinterpret, simplify, relocate or restyle any of the following:
- the same young woman and the same facial features. Her head is re-angled as described above, but
  no facial feature may change: the same eye shape, the same nose, the same mouth, the same face
  proportions and the same apparent age.
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

DO NOT INCLUDE: the same pose as image 1, head lowered, chin down, looking at the viewer, eye
contact with the camera, gaze toward the camera, no hands in frame, 3D rendering, CGI, thick
impasto oil painting, cel shading, flat hard-edged colour blocks, clean closed vector linework,
black outlines, deep or dramatic shadows, dark background, washed-out overexposed flat image,
saturated or neon colours, hue shift, recolouring, palette swap, colour cast toward grey-violet or
sage green, white or silver or platinum hair, pale desaturated grey-blue eyes, monochrome
conversion, full greyscale, bokeh, sparkles, particles, paper or film grain, watermark, signature,
text.
```

---

## 2. 完整提示词 · 中文版（v2）

```
随附三张图。图1 是内容与身份；图2 是画法参考；图3 是姿态参考。
三张图各取各的，不要越界。

全图只有下面这两处会变，其余一切都保持图1 原样：
1) 人物的姿态。图1 自己的姿态要被替换掉，不是保留。
   - 图1 现在是什么样：头回望观者、头微微低着、画面里看不到手
   - 结果必须变成什么样：头转向画面右侧并微微上抬，视线落向画面右上、画外，
     不再看着观者；双手都出现在画面里，在胸前抱着一本合上的书
   - 自检：如果成图里她仍在看着观者、头仍然低着、或者看不到手，
     说明姿态没有被应用，请修好再输出。
2) 一本双手抱着的合上的硬壳书。图1 里完全没有它。
其余全部内容——脸与五官、头发、所有饰品、服装、背景，以及每一种颜色——都按下面写的从图1 保留。

姿态（照图3 来）。按下面这个重要性顺序执行：如果无法全部满足，
先保住靠前的项，让靠后的项让步：
1. 头与视线（最重要）：头转向画面右侧并微微上抬，下巴略高于肩线；
   视线落向画面右上、画外；眼睛不与观者对视。表情安静、淡淡的分神，嘴唇轻抿。
2. 身体与肩：身体侧转约四分之三，肩线倾斜，可见的耳朵在画面左侧。
3. 手与书：两条前臂从下方伸上来，在胸前交叠。一本合上的硬壳书横抱在胸前，
   接近水平，只有约 10 到 20 度的轻微倾斜；封面朝观者，白色书口在书的左侧。
   画面右侧的手搭在封面右上部分、手指朝左内扣、指节朝观者；
   画面左侧的手从下方托住书的左下角。
4. 裁切（最不重要）：下缘裁切下移到腰与髋之间，
   让双臂、双手和整本书都装进画面。

保持图1 不变（这是对已有角色的迁移，不是重新设计；不要重新诠释、简化、挪动或改变任何一项）：
同一个年轻女性、同一套五官。她的头按上面写的方式重新摆角度，
但五官特征一个都不能变——同样的眼型、鼻形、嘴形、面部比例和年龄感；
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

不要出现：与图1 相同的姿态、头低着、下巴向下、看着观者、与镜头对视、视线朝向镜头、
画面里没有手；3D 渲染、厚涂、赛璐璐平涂、干净闭合的矢量线稿、黑色轮廓线、深阴影、暗背景、
过曝发白的扁平画面、高饱和荧光色、换色、调色板替换、往灰紫或鼠尾草绿偏色、
白色或银灰或铂金发色、褪成灰蓝的眼睛、改成黑白或全灰、光斑粒子、颗粒纹理、水印签名文字。
```

---

## 3. 备选：短版（若 v2 姿态仍不生效再用）

原理：姿态没被执行时，最有用的手段不是继续加句子，而是**把"不要改"的内容砍掉，让姿态成为提示词的主体**。
这一版只保留最关键的几项身份锚点（发色、眼睛、三朵花、小痣），其余细节主动放弃。

```
Three images: image 1 = content and identity, image 2 = style, image 3 = pose.

REPLACE IMAGE 1'S POSE WITH IMAGE 3'S POSE. Image 1 currently shows the head looking back at the
viewer with the head slightly lowered and no hands in frame. That pose must NOT survive.
The result must show: the head turned toward the RIGHT side of the frame and tilted slightly UP,
the chin a little above the shoulder line, the gaze going toward the upper right and off-screen,
NOT meeting the viewer's eyes; the visible ear on the LEFT side of the frame; both forearms coming
up from below and crossing in front of the torso; and both hands holding one closed hardcover book
ACROSS the chest, almost horizontal (only 10 to 20 degrees of tilt), cover facing the viewer, white
page block along the LEFT edge, the right hand on the upper right part of the cover with the fingers
curling inward toward the left, the left hand supporting the book from beneath at its lower-left
corner. Extend the bottom crop to between the waist and the hip so the hands and the book fit.
If the head still looks at the viewer or is still lowered, the pose was not applied.

KEEP from image 1, unchanged: her face and every facial feature; her hair colour — a muted warm
ash-taupe with a faint yellow-green cast, around #8C8C83, NOT white, NOT silver, NOT platinum;
her straight long hair with long bangs and thin loose strands crossing the face; the exact three
long-pointed flowers above the right ear; the single small beauty mark under the same eye; her
bright saturated cyan-blue eyes, kept vivid and not desaturated; the white star-shaped hair
ornaments on the left, the blue X hair clip, the black-and-white checkered choker with its white
lace trim and cyan gemstone pendant, the checkered earring with the long cyan feather, and the
sheer white lace bodice with its snowflake appliqué (sleeveless, no sleeves added). Her own colours
must not change anywhere, and her background must keep its structure and its grey-green and olive
hues with the same left-brighter / right-darker balance.

The book does not exist in image 1: give it a muted grey-olive cover taken from image 1's own
palette, and take its horizontal two-handed gesture from image 3. Do not copy the vertically held
book of image 2.

RENDER in the technique of image 2: japanese anime watercolor and colored pencil, broken pencil
sketch lineart with tapered stroke ends and open contours, faint watercolor wash with soft bleeding
edges, visible brush marks, soft diffuse frontal top light, no cast shadows, no black, deepest
tones lifted to mid-value, three flat tonal steps, very low saturation, soft edges, no grain.
Keep the image high-key but do not wash it out: content-area mean brightness about 0.72-0.78,
5th-percentile about 0.40-0.55.

Do not include: image 1's original pose, a lowered head, eye contact with the camera, no hands,
silver or white or platinum hair, sleeves, 3D rendering, cel shading, closed vector linework,
dramatic shadows, overexposed flat white image, watermark or signature.
```

---

## 4. 出图时怎么判断姿态有没有生效

先看这三条（顺序即优先级）：

1. **头**：她是在看观者，还是转向画面右上、下巴略抬？——若还在看观者，姿态基本没生效，直接重跑，别在其余项上纠结。
2. **视线**：眼睛是否落在画外右上？有没有与镜头对视？
3. **手与书**：能否看到两只手 + 一本书横在胸前？

三层都对了再去看身份项（发色、眼睛、花、痣）。**顺序很重要**——如果头没转，说明姿态整体失效，
此时去挑剔发色没有意义，应当换用第 3 节的短版重跑。
