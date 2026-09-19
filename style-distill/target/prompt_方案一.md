# 目标图改图 prompt · 方案一 / 1A

**目标图**：`style-distill/target/target.png`（837×1243，比例 0.673）
**基准风格图**：`C:\Users\typ\Desktop\mantu` 里任选 2–3 张（建议 **1A37 / C8BE** 这两张鼠尾草米白的，
笔画最典型；或 **32A9 / FD7A** 若要更强的紫灰对比）
**铁律 A**：只迁移手法，不迁移配色。目标图的灰亚麻发、蓝眼、蓝羽毛、暖橄榄背景全部保持原样。

---

## 1. 目标图基线 vs 风格要求（实测）

| 指标 | 目标图实测 | 风格要求 | 要不要改 |
|---|---|---|---|
| **内容饱和度** | **0.077** | ~0.085 | ✅ **不用改**（`--sat-scale 1.0`） |
| 明度均值 | 0.496 | ≥0.60 | ⬆️ 抬高 |
| 亮度 P05 | 0.291 | ≥0.35 | ⬆️ 抬暗部 |
| 最暗像素 | **0.048** | ≥0.15（风格 0.166–0.320） | ⬆️ 消灭深黑 |
| 亮度 <0.35 的像素 | **19.4%** | — | ⬆️ 这 19.4% 都要抬 |
| 亮度 <0.20 的像素 | 0.319% | ~0 | ⬆️ 消灭 |
| 纯白(>0.97) 占比 | 0.006 | 0.446–0.624 | ⚠️ **方案一不适用**（保背景） |
| 笔触密度 | 1.98 | ~2.9（1.99–3.58） | ⬆️ 加线稿与笔触 |
| 色相族 | 橙棕 44% · 黄 35% · 绿 11% · 蓝 3% | 紫罗兰/蓝为主 | ❌ **不改**（铁律 A） |

**两个好消息**：
1. 目标图饱和度 0.077 已经**正好在风格水平**——所以「保色相」和「1A 低饱和」在这张图上**不冲突**，
   `--sat-scale` 用默认 1.0 即可，不需要做取舍。
2. 目标图**本来就没有黑**到不可救的程度：亮度 <0.20 的像素只占 0.319%（风格要 ~0）。

**一个必须知道的代价**：目标图有 **19.4% 的像素亮度低于 0.35**。1A 要把它们全部抬起来，
这会让这幅画原本的明暗纵深明显变平。这是 1A 的预期效果，不是 bug。

### 1A 明暗预览（已生成，动手前先看）

我用纯像素运算把 1A 的明暗部分单独模拟了出来（只改 L，色相与彩度原封不动，**不含笔触与线稿**）：
`style-distill/target/preview_1A.png` —— `python style-distill/tone_preview.py target/target.png -o target/preview_1A.png --floor 0.40`

| 指标 | 原图 | 1A 预览 | 风格要求 |
|---|---|---|---|
| 最暗像素 | 0.048 | **0.430** | ≥0.15（风格 0.166–0.320） |
| 亮度 P05 | 0.292 | **0.506** | ≥0.35（风格 0.387–0.616） |
| 明度均值 | 0.480 | **0.668** | ≥0.60 |
| 亮度 <0.20 占比 | 0.319% | **0%** | ~0 |
| 亮度 <0.35 占比 | 19.374% | **0%** | — |

**看完预览的两个结论**：

1. **代价确认**：画面明显变平，肩部与衣料的体积感大幅削弱，原来那种幽暗纵深没了。这是真的。
2. **意外的好消息**：明度抬起来之后，**那些细密识别点反而更清楚了**——黑白棋盘颈饰、雪花蕾丝、星形发饰、
   蓝羽毛、蓝宝石、蓝 X 发夹全都浮出来了，原来它们都埋在暗部里。
   所以对**这张图**而言，1A 不只是代价，也在帮识别度。
   ⚠️ 但注意：预览是**同一张图只改明度**，细节天然保留；真实生成时模型会重绘，
   细节仍需靠 PRESERVE 段与低 denoise 守住（见第 6 节风险 1）。


---

## 2. PRESERVE 段（逐项，按实际画面写）

以下全部来自放大核对，**替换掉任何模板化的泛称**：

- **人物与姿态**：单人年轻女性，半身；肩线朝**远离观者**的方向转，脸**回望观者**，头略低，表情安静寡淡。
- **头发**：长直发，**灰亚麻/灰褐色带浅黄绿调**（`#A6A397` 一带）；长刘海遮额；
  **数缕细长发丝横过脸前**（这是这幅画的显著特征，务必保留）；长发垂至画面下方。
- **发间小物**：
  - 画面**左侧**发间散布 **3–4 枚白色小星形发饰**
  - 右侧刘海处一枚**浅蓝色 X（叉）形发夹**
- **眼睛**：**明亮青蓝色**（`#4E7185` 一带），内有大块白色高光；深色眼线，**根根分明的长睫毛**；
  **右眼（画面右侧那只）下方一颗小痣**。
- **头饰**：画面右侧、耳上方至头顶，一组 **3 朵白色至淡紫的五/六瓣长尖瓣花**（百合/星花状，不是圆瓣花）。
- **耳饰**：**右耳一枚黑白棋盘格圆片 + 一条长青蓝色羽毛垂坠**（羽毛有细密羽枝，上方连细链）。
- **颈饰**：**黑白小格棋盘纹缎带**，上缘缀一圈**白色雪花/星形蕾丝花边**；
  另有一条细链与一枚**青蓝色圆形宝石（凸圆面）吊坠**。
- **服装**：**白色半透明蕾丝罩衫/抹胸**，胸前覆大量**白色雪花形与叶片状蕾丝贴花**（雪花图案要保留）；肩与颈裸露。
- **背景**（保留结构，只简化提亮）：
  - 整体为**灰绿 / 橄榄色的大块柔和面**，另有淡奶白与浅灰的几何面
  - 画面右侧中上部一枚**大型浅色圆形形状**（圆盘/荷叶状）
  - 画面右侧有一根**带斜纹的竖直绳索/绒线**自上下贯穿
  - **明暗不对称：画面左侧偏亮、右侧偏暗**——这个关系要保留
- **材质**：柔和笔刷/喷枪渐变，边缘柔，几乎无硬线稿（这正是要改造的地方）。

---

## 3. 完整 prompt（英文 · 双段式 · 可直接粘贴）

> 上传顺序：**两张图都要传**。文本里按内容点名，避免顺序不稳定导致角色互换。

```
The first image is the STYLE DONOR: a watercolor-and-pencil anime illustration of a girl holding
a notebook. The second image is the CONTENT: the pale-haired girl with white lily flowers and a
blue feather earring. Use ONLY the rendering style of the first image, and ONLY the subject,
composition and colours of the second image. Ignore all subject matter, characters, hairstyles,
clothing, props and every colour of the first image.

PRESERVE EXACTLY from the second image — this is a rendering-style transfer of an existing
illustration, not a redesign. Do not reinterpret, simplify, relocate or restyle anything:
- the same young woman, half-body, shoulders turned away from the viewer, face looking back over
  the shoulder toward the viewer, head slightly lowered, quiet subdued expression
- the same long straight ash-taupe hair with a faint yellow-green cast, long bangs covering the
  forehead, several thin loose strands crossing in front of the face, hair falling past the
  bottom of the frame
- the white star-shaped hair ornaments scattered in the hair on the left side, and the light blue
  X-shaped hair clip in the bangs on the right side
- the same bright cyan-blue eyes with large white highlights, dark eyeliner, long distinctly
  separated eyelashes, and the small beauty mark under the right eye
- the same cluster of three white-to-pale-lilac five/six-petalled long-pointed lily-like flowers
  above the right ear
- the same right-ear earring: a black-and-white checkerboard disc with a long cyan-blue feather
  hanging beneath it on a fine chain
- the same choker: a black-and-white fine checkerboard ribbon trimmed with a row of white
  snowflake-and-star lace, plus a fine chain and a round cabochon cyan gemstone pendant
- the same sheer white translucent lace bodice covered with white snowflake-shaped and
  leaf-shaped lace appliqué, bare shoulders and neck
- the same background structure: soft grey-green and olive planar shapes with pale cream and grey
  facets, the large pale circular disc shape at the upper right, the vertical braided cord with
  diagonal hatching running down the right side, and the same left-brighter / right-darker
  asymmetry
- the same framing and crop

COLOUR IDENTITY LOCK — the second image keeps its own colours. Treat the colour rendering below
as a technique only; never adopt any hue, colour or palette from the first image. Keep the ash
taupe hair its own colour, keep the cyan-blue eyes, the blue feather, the blue gemstone, the blue
hair clip, the skin tone, the white lace, the black-and-white checkered patterns and the
grey-green / olive background exactly as they are. Do not recolour, do not swap palettes, do not
shift anything toward grey-violet, sage green or lavender. Shadows and highlights must be derived
from each element's OWN colour (its own hue, only lighter or darker and less saturated) — not
replaced by any fixed grey, violet or blue.

STYLE TO APPLY — technique only, no palette:
Redraw the whole image as a japanese anime illustration rendered in traditional watercolor and
colored pencil media. Add soft delicate pencil sketch lineart: broken and intermittent contours
with varied line weight, tapered stroke ends and overlapping resketch strokes; contours stay
slightly open and unfinished rather than fully closed. Colouring becomes a faint watercolor wash
with soft bleeding edges that slightly overflow the lineart, plus visible brush sweep marks;
highlights are made by lightening each element's own hue rather than by adding white. Lighting
flattens to a soft diffuse light from the front and slightly above: no cast shadows, no hard
shadow edges, no rim light, no bloom. Compress the tonal range to roughly three flat steps —
light, mid and a lifted dark. Lift the deepest tones up to mid-value: there must be NO black
anywhere, and no area darker than about 45 percent value. Keep the overall image high-key and
airy with the content-area brightness raised well above its current level, and keep contrast low.
Keep the existing low saturation roughly as it is — do not reduce it further and do not increase
it. Edges stay soft, never crisp or glossy; no grain, no film texture, no canvas texture.
Simplify the background in DETAIL only — reduce its detail density and summarise its shapes, lift
its values so no part of it goes dark, but keep every element in place, keep its grey-green and
olive hue family, and keep its left-bright / right-dark relationship. Do not replace, relocate,
delete or recolour any background element, and do not add any new element.

MOOD: quiet, gentle, introspective, wistful and literary. Airy and light, never heavy or dark.

DO NOT INCLUDE: 3D rendering, CGI, thick impasto oil painting, cel shading, flat hard-edged
colour blocks, clean closed vector linework, black outlines, deep or dramatic shadows, dark
background, saturated or neon colours, hue shift, recolouring, palette swap, colour cast toward
grey-violet or sage green, monochrome conversion, full greyscale, bokeh, sparkles, particles,
paper or film grain, watermark, signature, text.
```

---

## 4. 中文版（给中文自然语言接口）

```
第一张图只是画法参考，第二张图才是要改的内容。只取第一张图的画法，内容、构图、颜色全部以
第二张图为准。第一张图里的人物、发型、服装、道具和所有颜色一律不要。

保持第二张图原样不变（这是一次画法迁移，不是重新设计，不要重新诠释、简化、挪动或改变任何元素）：
同一个年轻女性，半身，肩线朝远离观者的方向转，脸回望观者，头略低，表情安静；
同一头长直灰亚麻色（带一点浅黄绿调）头发，长刘海，数缕细发丝横过脸前，长发垂到画面下方；
发间左侧的白色星形发饰，右侧刘海里那枚浅蓝色 X 形发夹；
同一双明亮的青蓝色眼睛（带大块白高光）、深色眼线、根根分明的长睫毛、右眼下方那颗小痣；
右耳上方那三朵白色到淡紫的五/六瓣长尖瓣花；
右耳那枚黑白棋盘格圆片 + 长青蓝色羽毛垂坠耳饰；
颈部那条黑白小格棋盘纹缎带（上缘一圈白色雪花蕾丝）+ 细链 + 青蓝色圆形宝石吊坠；
那件白色半透明蕾丝罩衫，胸前覆着白色雪花形与叶片状蕾丝贴花，肩颈裸露；
背景结构照旧：灰绿与橄榄色块面、淡奶白与浅灰的几何面、右上那枚大型浅色圆形、
右侧那根带斜纹的竖直绳索，以及左亮右暗的关系；
裁切与画幅不变。

颜色规则（重要）：第二张图每个元素自己的颜色一律保持——灰亚麻发、青蓝眼睛、蓝羽毛、
蓝宝石、蓝发夹、肤色、白色蕾丝、黑白棋盘格、灰绿与橄榄色背景全部不变。
不要换色、不要调色板替换、不要往灰紫或鼠尾草绿上靠。
暗部与高光从每个元素自己的色相派生（自身色相压暗/提亮），不要统一换成灰或蓝。

只改画法：改造成水彩与彩铅手绘质感的日系动漫插画。加上柔和的铅笔草稿线——
断续、粗细变化、收笔出锋、叠线重描，轮廓不必闭合。上色改成极淡的水彩洗笔，
边界模糊渗染、允许轻微溢出线外，保留扫笔擦痕；高光靠把该元素自身色相提亮来表现，
不要靠加白。光改成正面偏上方的柔和散射光：去掉投影、硬边阴影、轮廓光与光晕。
明暗压成三档（亮、中、被抬高的暗），把最暗处抬到中等明度——
画面里不要有黑色，也不要有任何低于约四成明度的区域。整体抬高明度，保持通透，压低对比。
饱和度保持现在的低水平，不要再降也不要升。
背景只简化细节与提亮明度（去掉细碎细节、概括形状、不让任何区域变暗），
但元素位置、灰绿橄榄色相族、左亮右暗的关系全部保留；不要替换、挪动、删除或改色，也不要新增元素。
边缘保持柔，不要锐利、不要塑料光泽。

氛围安静、温柔、内敛、带书卷气，通透轻盈，不要沉闷发暗。

不要：3D 渲染、厚涂、赛璐璐平涂、干净闭合的矢量线稿、黑色轮廓线、深阴影、暗背景、
高饱和荧光色、换色、调色板替换、往灰紫或鼠尾草绿偏色、改成黑白或全灰、光斑粒子、颗粒纹理、
水印签名文字。
```

---

## 5. 操作步骤

### 5.0 基准图（风格来源）怎么选 ★

**术语**：**基准图 = 风格来源图（style donor）**＝`C:\Users\typ\Desktop\mantu` 里那 13 张；
**目标图 = 内容来源**＝你这张灰亚麻发少女。基准图只提供**画法**，不提供内容与配色。

**13 张里任意挑都能用**（因为铁律 A 让配色不迁移），但**它们并不等价**，差在四个轴上：

| 轴 | 为什么重要 | 怎么挑 |
|---|---|---|
| **① 先验重合度** | 基准图里也有浅发少女，与你**目标图同为浅发半身像**——这正是上次身份漂移翻车的模式 | ⚠️ **避开 A 组那 5 张银灰浅发**（187D / 1A37 / 47EC / C8BE / EB7D），改挑深发角色 |
| **② 色相外泄** | 基准图是冷灰紫系，你目标图是暖灰绿系；模型会不由自主往参考的色系偏 | 跨配色分支选，或靠 `preserve_hue.py` 兜底 |
| **③ 笔触密度** | 你要"加线稿"，但目标图本来几乎无线稿（1.98） | 挑 Sobel 梯度高的：E2E3 3.51 · 57A8 3.22 · 78A4 3.14 |
| **④ 前景手势/道具泄漏** | 基准图的手势与道具也可能被搬过去 | ⚠️ **不要同时用两张"手扶眼镜"的**（57A8 / 32A9 / 78A4 任两张）——你目标图没眼镜，会被加上 |

**逐张速查**（分支 / 发色 / 笔触密度 / 前景手势，含高饱和道具）：

| 图 | 分支 | 发色 | 笔触密度 | 手势·道具 | 备注 |
|---|---|---|---|---|---|
| E2E3 | C | 深蓝黑 | **3.51** | 举叉·蛋糕 | ★ 有粉草莓（0.39% 面积，影响小） |
| 57A8 | C | 深墨 | **3.22** | **扶眼镜**·文件夹 | 与 32A9/78A4 互斥 |
| 78A4 | C | 灰 | 3.14 | **扶眼镜**·**红电话** | ❌ 红电话占 1.05% 易泄漏 |
| 32A9 | B | 深紫灰 | 2.61 | **扶眼镜**·笔记本 | |
| B325 | C | 蓝紫 | 2.66 | 抱书 | |
| FD7A | B | 深墨 | 2.46 | 笔抵下巴 | |
| A290 | B | 灰紫 | 2.32 | 棒棒糖 | |
| 8B23 | B | 深墨 | 1.99 | 笔抵下巴 | 笔触过弱 |
| 187D·1A37·47EC·C8BE·EB7D | A | **银灰浅发** | 2.98–3.58 | 抱书·托腮 | ❌ **与目标图撞先验** |

**推荐**：
- **首选 `E2E346188F5C9E942209EC1CF19DB71F` + `32A9A9E0B1A96F7AB5DB8CAB0F13FB70`**
  —— 笔触密度最高的一对（3.51 / 2.61）、**跨配色分支**（C+B，配色差得越远，模型越容易分离出"共同的手法是笔触与明度"）、
  发色都是深色（与目标图差异大）、手势不重叠（举叉 vs 扶眼镜）。
- **替代**：`E2E3` + `FD7A`；或 `57A8` + `A290`。
- **张数**：**2 张最稳**，1–3 张都在合理区；**不要一次塞 13 张**——参考图越多，
  越容易把它当成"内容"去做平均。

> **⚠️ 修正上一轮的建议**：我先前说"用 1A37 + C8BE 这两张鼠尾草米白的，笔画最典型"——
> 那两张恰好是**银灰浅发**，与你目标图的浅发**先验重合最高**。作废，改用上面这对深发的。

**注意**：以上全部针对"基准图取自这 13 张"。
如果你上传的是**这 13 张以外**的图，这份蒸馏里的手法描述（水彩彩铅 / 低饱和 / 无黑 / 铅笔断线）
就跟那张图不一致了——那种情况要么改用通用短 prompt，要么让我重新蒸馏那张。

### 5.1 上传与参数

1. **上传**：目标图 + 2 张风格图（选法见 5.0）。文本里已按内容点名（"the pale-haired girl with lily
   flowers" / "the girl holding a notebook"），不依赖上传顺序。
2. **尺寸**：跟随目标图比例 **0.673**（约 2:3）。不要用 3:4。
3. `quality=high`，`n=1` 起，最多 2–4 张选优。
4. **重跑顺序**：
   - 若明度没抬上去（仍发暗）→ 把 `Lift the deepest tones…` 与 `high-key and airy` 提到 STYLE 段最前
   - 若花/羽毛/棋盘格被简化掉 → 缩短 STYLE 段，把 PRESERVE 段整体前移，并再加一句
     `Do not simplify, relocate or restyle any accessory, ornament or garment detail.`
   - 若发色或背景被推向鼠尾草绿/灰紫 → 把 `COLOUR IDENTITY LOCK` 段提到 STYLE 段**之前**
5. **色相兜底**（若几何没大改）：
   ```
   python style-distill/preserve_hue.py --style-output <生成图> --original style-distill/target/target.png \
       -o style-distill/target/fixed.png --sat-scale 1.0 --chroma-blur 4
   ```
   `--sat-scale 1.0`（这张图的饱和度本来就对，不要压）；几何有位移时 `--chroma-blur` 提到 4–8。
6. **验收**：
   ```
   python style-distill/analyze_style.py style-distill/target -o style-distill/target/after_stats.json
   ```
   达标线：最暗像素明度 ≥0.15 · 亮度 P05 ≥0.35 · 内容明度均值 ≥0.60 ·
   **内容饱和度仍在 0.07–0.10 之间（没被改）** · 灰亚麻发/青蓝眼/蓝羽毛/白蕾丝/灰绿背景的色相未变。

---

## 6. 这张图的特定风险（按严重度）

1. **细节被简化**（最高）：黑白棋盘格、雪花蕾丝、星形发饰、羽毛羽枝这些**细密图案**是本次迁移最容易丢的东西——
   把"柔边笔刷画"改成"线稿 + 水彩"，模型倾向于把碎细节概括掉。而它们恰恰是这张图的识别点。
   → 所以参考图只用 2 张、PRESERVE 段逐项写死、必要时优先保线结构而非追求风格浓度。
2. **明暗被压平**：19.4% 的像素要被抬亮，画面纵深会明显变浅（见第 1 节）。这是 1A 的预期代价。
3. **配色被带偏**：基准图是冷灰紫系，本图是暖灰绿系。不加 `COLOUR IDENTITY LOCK`，
   模型极可能把背景推向鼠尾草绿、把发色推向银灰——这正是铁律 A 要防的。
   → 参考图按 5.0 挑**深发**的，可显著降低这一风险（浅发基准图与你有先验重合）。
4. **基准图的手势/道具泄漏**：你目标图没眼镜，但 57A8 / 32A9 / 78A4 三张都是"手扶眼镜"。
   → 按 5.0 的硬约束，**不要同时用其中两张**，否则容易被加上眼镜。
5. **蓝色点缀太细小**：蓝眼 + 蓝羽 + 蓝宝石 + 蓝发夹合计只占 **0.202%** 的像素（2103 px）。
   这么小的面积在重绘中最容易被抹掉或改色。→ `preserve_hue.py` 的 `--sat-scale 1.0` 能兜住；
   纯靠提示词的话，务必在 PRESERVE 里逐个点名（已写）。
6. **背景的竖直绳索与圆形**：结构性强、容易在"简化背景"时被删。PRESERVE 里已点名，
   且 STYLE 段的背景指令明确写了 *keep every element in place*。
