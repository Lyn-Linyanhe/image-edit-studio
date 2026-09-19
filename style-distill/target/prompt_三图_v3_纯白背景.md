# 提示词 v3 · 人物以外纯白背景（在 v2 姿态优化版基础上）

**本版相对 v2 只改背景要求**，姿态优化与角色分工全部保留。

| 编号 | 文件 | 角色 |
|---|---|---|
| **图1** | `43e24ec8…png` | 内容与身份 |
| **图2** | `47ec32ac…jpg` | 画法 / 风格 |
| **图3** | `187dafa4…jpg` | 姿态 |

---

## 0. 改背景带来的三处连锁改动（必须同步，否则自相矛盾）

| # | 改动 | 原因 |
|---|---|---|
| 1 | **变更清单从 2 条变 3 条**：新增"背景换成纯白纸底" | 我上一版刚把"要改什么"提到最前面，清单必须**完整**；漏掉背景会让模型以为背景不该动 |
| 2 | **删掉 PRESERVE 里的"保留背景结构"整条** | 否则"背景元素位置一律不动"与"背景全白"直接打架——**自相矛盾是提示词失效的头号原因** |
| 3 | **验收线新增"纯白占比"** | 白底方案下 `纯白(>0.97) 占比 ≥0.35` 终于适用了（方案一时我明确说过它不适用） |

### 白底上特有的新风险（必须防）

目标图本身是**浅白发 + 白色半透明蕾丝罩衫**。放到纯白背景上，**人物边缘极易与背景糊成一片**。

正规解法（也是这套风格本来的做法）：**靠铅笔线稿把轮廓勾出来**，而不是靠阴影或投影。
所以 prompt 里专门有一段要求：头发的每缕轮廓、肩线、手臂、蕾丝边缘**都要有线**；
且**禁止任何投影/地面阴影/外发光**——白底上画阴影会立刻露出破绽。

### 背景元素必须"删干净"（模型的常见残留）

原图背景里有：灰绿与橄榄色块面、淡奶白与浅灰几何面、右上**大型浅色圆形**、右侧**带斜纹的竖直绳索**。
这四类在成图里**一个都不能留**——尤其那个大圆和竖直绳索结构性强，残留下来的概率最高。prompt 里逐个点名删除。

### 关于"纯白"的准确含义

是**纸白**（与图2/图3 一致的暖白纸底，约 `#F2EBED` 一带），不是冷调的 `#FFFFFF`。
这与参考图的纸质感一致；同时明确禁止渐变、暗角、纹理与色偏。

---

## 1. 完整提示词 · 英文版（v3）

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
3) The BACKGROUND. Everything that is not the figure must become blank paper white. The entire
   existing background is REMOVED (see below) — this is a deletion, not a simplification.
Everything else — the face and its features, the hair, every ornament, the garment, and every
colour — is preserved from image 1 exactly as described further below.

BACKGROUND — replace it entirely with plain paper white:
Delete the whole existing background. Specifically, none of the following may survive anywhere in
the picture: the soft grey-green and olive planar shapes; the pale cream and grey facets; the large
pale circular disc shape at the upper right; the vertical braided cord with diagonal hatching on
the right side; any architectural shape, any drapery, any abstract form. All of them must be gone,
leaving nothing but empty paper.
Fill the entire background with blank paper white — the same warm paper white used in images 2 and
3 (around #F2EBED), not a cold digital #FFFFFF. It must be completely flat and empty: no colour
cast, no gradient, no vignette, no texture, no paper grain, no pattern, no shapes, no light spots,
no sparkles, no particles and no border.
Only the figure remains on that white: her body, hair, face, ornaments, garment, and the hands and
book added above. Nothing else is in the frame.
THE FIGURE MUST READ CLEARLY AGAINST THE WHITE. Because her hair is pale and her bodice is white,
make sure every silhouette edge is defined: keep the pencil lineart along every hair lock, the
shoulders, the arms, the hands, the book's edges, the lace trim and the lace appliqué, so the
figure separates from the paper by LINE, not by shadow. Do not lose the hair outline and do not
lose the lace outline.
Do NOT add any cast shadow, ground shadow, contact shadow, drop shadow, outline glow or halo around
the figure, and do not darken the paper near her. The background stays pure blank white everywhere.

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
  three, petals long and pointed, not round. They rotate with the head, and they now sit against
  the white — keep their petal outlines so they still read.
- the same right-ear earring: a black-and-white checkerboard disc with a long cyan-blue feather
  hanging beneath it on a fine chain; it rotates with the head.
- the same choker: a black-and-white fine checkerboard ribbon trimmed with a row of white
  snowflake-and-star lace, plus a fine chain and a round cabochon cyan gemstone pendant
- the same sheer white translucent lace bodice covered with white snowflake-shaped and
  leaf-shaped lace appliqué. Continue the SAME garment downward over the newly visible lower torso;
  keep it off-shoulder and sleeveless. Do NOT add sleeves and do NOT substitute another garment.
  Because the bodice is white on a white background, define its edges and its lace with lineart.

THE BOOK — the book does not exist in image 1, so give it a colour taken from image 1's own
palette: a muted grey-olive cover in the same warm grey-olive family as image 1's clothing tones.
Take its GESTURE (horizontal, both hands) from image 3. Do NOT copy the book or the book gesture of
image 2 — image 2's book is held vertically with one hand at its top edge and that orientation must
not appear.

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
and shadow steps remain readable. Do not flatten everything into near-white, and keep the figure
distinct from the white background.

MOOD: quiet, gentle, introspective, wistful and literary. Airy and light, never heavy or dark.

DO NOT TAKE FROM IMAGE 2 (style only): its silver-grey hair colour, its over-the-shoulder
look-back head angle, its vertically held book and its one-hand grip on the book's top edge, its
sage green ribbon bow, its knitwear, its facial features, its 3:4 aspect ratio.

DO NOT TAKE FROM IMAGE 3 (pose only): its silver-grey hair colour, its sage green ribbon bow, its
cream turtleneck and sage cardigan, the dark sage green cover of its book, its facial features, its
3:4 aspect ratio and its author signature.

DO NOT INCLUDE: any part of image 1's original background — the grey-green and olive planar shapes,
the pale cream and grey facets, the large pale circular disc, the vertical braided cord with
diagonal hatching, any architectural or abstract shape, any colour in the background, any gradient,
vignette, texture, grain, sparkle or border; any cast shadow, ground shadow, contact shadow, drop
shadow, rim glow or halo around the figure; the same pose as image 1, head lowered, chin down,
looking at the viewer, eye contact with the camera, no hands in frame; 3D rendering, CGI, thick
impasto oil painting, cel shading, flat hard-edged colour blocks, clean closed vector linework,
black outlines, deep or dramatic shadows, dark background, washed-out overexposed flat image,
saturated or neon colours, hue shift, recolouring, palette swap, colour cast toward grey-violet or
sage green, white or silver or platinum hair, pale desaturated grey-blue eyes, monochrome
conversion, full greyscale, watermark, signature, text.
```

---

## 2. 完整提示词 · 中文版（v3）

```
随附三张图。图1 是内容与身份；图2 是画法参考；图3 是姿态参考。
三张图各取各的，不要越界。

全图只有下面这三处会变，其余一切都保持图1 原样：
1) 人物的姿态。图1 自己的姿态要被替换掉，不是保留。
   - 图1 现在是什么样：头回望观者、头微微低着、画面里看不到手
   - 结果必须变成什么样：头转向画面右侧并微微上抬，视线落向画面右上、画外，
     不再看着观者；双手都出现在画面里，在胸前抱着一本合上的书
   - 自检：如果成图里她仍在看着观者、头仍然低着、或者看不到手，
     说明姿态没有被应用，请修好再输出。
2) 一本双手抱着的合上的硬壳书。图1 里完全没有它。
3) 背景。人物以外的一切都变成纯白纸底。原来的背景是整体删除，不是简化。
其余全部内容——脸与五官、头发、所有饰品、服装，以及每一种颜色——都按下面写的从图1 保留。

背景——整体换成纯白纸底：
把原来的背景全部删掉。下面这些一律不许在画面里留下：灰绿与橄榄色块面；
淡奶白与浅灰的几何色块；右上那枚大型浅色圆形；右侧那根带斜纹的竖直绳索；
任何建筑形状、任何布料褶皱、任何抽象形状。全部消失，什么都不留。
整个背景填成空白纸白——与图2、图3 一样的暖纸白（约 #F2EBED），
不是冷调的数码 #FFFFFF。必须完全平、完全空：无色偏、无渐变、无暗角、无纹理、无纸纹、
无图案、无形状、无光斑、无粒子、无边框。
白底上只剩下人物：她的身体、头发、脸、饰品、服装，以及上面新加的手和书。画面里没有别的东西。
人物必须在白底上清晰可辨。因为她的头发是浅色、罩衫是白色，
所以每一条轮廓都要有线：每一缕头发的轮廓、肩线、手臂、手、书边、
蕾丝花边与蕾丝贴花，都要保留铅笔线稿，让轮廓靠"线"与纸面分开，而不是靠阴影。
不要丢掉头发的外轮廓，也不要丢掉蕾丝的外轮廓。
不要在人物周围加任何投影、地面阴影、接触阴影、外发光或光晕，也不要把人物附近的纸面压暗。
背景处处保持纯白。

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

保持图1 以下各项不变（不要重新诠释、简化、挪动或改变）：
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
它们现在贴在白底上，花瓣轮廓要留住，别让它们和白底糊在一起；
右耳那枚黑白棋盘格圆片 + 垂下的长青蓝色羽毛耳饰，随头部一起转；
颈部那条黑白小格棋盘纹缎带（上缘一圈白色雪花蕾丝）+ 细链 + 青蓝凸圆宝石吊坠；
那件白色半透明蕾丝罩衫，胸前覆白色雪花形与叶片状蕾丝贴花；
下缘裁切下移后露出的下半身要延续同一件罩衫往下画，保持露肩无袖——不要加袖子，不要换成别的服装；
因为罩衫是白底上的白色，它的边缘和蕾丝花边要用线稿勾出来。

那本书：图1 里原本没有书，所以颜色要从图1 自己的配色里取——
用与图1 衣物同族的柔和暖灰橄榄色封面。
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
不要把一切压成接近纯白，要让人物与白背景分得开。

氛围安静、温柔、内敛、带书卷气，通透轻盈，不要沉闷发暗。

不要从图2 搬（它只给画法）：它的银灰色头发、它"侧身回眸"的头部角度、
它那本竖着抱的书和"一只手扣书的上缘"的握法、它的墨绿色缎带蝴蝶结、它的针织衣物、
它的五官、它的 3:4 画幅。

不要从图3 搬（它只给姿态）：它的银灰色头发、它的墨绿色缎带蝴蝶结、
它的米白高领针织与鼠尾草绿开衫、它那本书的墨绿封面、它的五官、
它的 3:4 画幅、它的署名水印。

不要出现：图1 原来背景的任何部分——灰绿与橄榄色块面、淡奶白与浅灰几何色块、
右上那枚大型浅色圆形、右侧那根带斜纹的竖直绳索、任何建筑或抽象形状、背景里的任何颜色、
任何渐变、暗角、纹理、颗粒、光斑或边框；
人物周围的任何投影、地面阴影、接触阴影、外发光或光晕；
与图1 相同的姿态、头低着、下巴向下、看着观者、与镜头对视、画面里没有手；
3D 渲染、厚涂、赛璐璐平涂、干净闭合的矢量线稿、黑色轮廓线、深阴影、暗背景、
过曝发白的扁平画面、高饱和荧光色、换色、调色板替换、往灰紫或鼠尾草绿偏色、
白色或银灰或铂金发色、褪成灰蓝的眼睛、改成黑白或全灰、水印签名文字。
```

---

## 3. 推荐做法：分两步走（比一次全改更可靠）

一次请求里同时要**换姿态 + 换背景**，风险叠加（头部重绘最容易漂移，背景删除最容易残留）。
而工具里刚好有一个**已验证的机制**可以拆开它们：**红色标记遮罩**（保护区域 100% 生效，实测过）。

| | 第一步：整张图 | 第二步：仅涂过的区域 |
|---|---|---|
| 模式 | 「整张图（无需涂遮罩）」 | 「仅涂过的区域（需要涂遮罩）」 |
| 输入 | 上一步的**输出图**作为新的「要改的图」 | 同上 |
| 参考图 | 图2 = 画法 / 风格；图3 = 姿态 | **图2 = 画法 / 风格**（姿态已定，不再需要） |
| 涂哪里 | 不涂 | **只涂背景**（人物、手、书都不涂） |
| 提示词 | 第 1/2 节的 v3 全文 | 见下方「第二步专用」 |
| 好处 | 专注把姿态做对 | **人物整块被保护**，只改背景；已验证 100% 不误改保护区 |

**第一步**：先只求"姿态 + 画法"做对、身份守住。背景就算没变白也没关系。

**第二步专用提示词**（很短，因为只做一件事）：

```
只改涂成红色的区域。红色区域是背景，请把它整块换成空白纸白——
与参考图一致的暖纸白（约 #F2EBED），不是冷调的数码白。
红色区域以外的一切（人物、头发、脸、饰品、服装、双手和书）必须逐像素保持原样，
不要重画、不要改色、不要移动。
背景要完全平、完全空：无色偏、无渐变、无暗角、无纹理、无纸纹、无形状、无光斑、无边框。
不要在人物周围加任何投影、地面阴影、接触阴影、外发光或光晕，也不要把人物附近的纸面压暗。
人物在白底上要清晰可辨：保留他头发、肩线、手臂、蕾丝与书边的铅笔线稿轮廓。
```

这样第二步的成功率会比"一次全改"高得多——因为它把最难的两件事拆开，且第二步用的是工具里唯一**经实测验证**的保护机制。

---

## 4. 验收

**姿态优先级先看**（顺序即优先级）：头是否转向画面右上并微抬 → 视线是否在画外右上 → 能否看到双手与横抱的书。

**然后看背景**：
- [ ] 背景**全部是纯白**，没有色块、没有大圆、没有竖直绳索（这四类是最容易残留的）
- [ ] **没有渐变、暗角、纹理、光斑、边框**
- [ ] 人物周围**没有投影/外发光/光晕**
- [ ] 人物的**头发、肩线、蕾丝、书边都有线稿轮廓**，没有与白底糊在一起
- [ ] 三朵花、白色星形发饰、蓝羽毛在白底上仍然清晰可辨

**最后看身份**：
- [ ] 发色**没变银灰**（仍是灰亚麻带黄绿）——始终是最高风险
- [ ] 眼睛仍是**高饱和青蓝**，不是灰蓝
- [ ] **只有一颗**小痣，且在**同一只眼**下方
- [ ] 五官没被"重画成另一个人"
- [ ] 书是**横**的（不是图2 的竖抱），封面是暖灰橄榄（不是墨绿）
- [ ] **没有袖子**
- [ ] 手指数量正常

**机检**（白底方案下这条终于适用了）：

```
python style-distill/analyze_style.py <输出图所在目录> -o style-distill/target/v3_stats.json
```

达标线：**纯白(>0.97) 占比 ≥0.35** · 亮度 P05 ≥0.35 · 内容明度均值 ≥0.60 · 最暗像素明度 ≥0.15 · 无黑。
另外跑 `compare_identity.py` 查发区明度与高饱和蓝占比有没有被漂。
