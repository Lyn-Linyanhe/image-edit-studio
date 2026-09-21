# 迁移方案 · 按你现有管线写（A–G 格式）

**管线前提**（沿用上次踩过坑的那套）：`参考图（风格） + 目标图（内容） + 文本 prompt` 的 edits 类接口。
这类接口**没有** denoise / mask / CFG / 独立负向通道，所以风格段写多长、写多具体，直接决定它是"换皮"还是"重画"。

**配套**：拆解依据见 `漫画风格蒸馏.md`；色板见 `palette.png`；结构化数据见 `style_card.json`。

---

## 0. 两条铁律与两个取舍

### 铁律 A · 只迁移手法，不迁移配色（最高优先级）

**目标图里每个元素自己的颜色一律不动。** 目标图头发是黄色就保持黄色，**不会因为基准图是红色就变红**，
也不会因为基准图是"银灰/灰紫"就被漂成银灰。除非你明确声明要换某个元素的颜色。

边界（这条直接来自你给的 7 维度框架——"主色/辅助色"与"饱和度/对比度/明暗"是分开的两项）：

| | 内容 | 迁移？ |
|---|---|---|
| **固有色相** | 头发黄、眼睛蓝、裙子红、皮肤色调、背景色相族 | ❌ **不迁移** |
| **色彩处理手法** | 饱和度压到极低 · 高调 · 低对比 · 无黑 · 抬暗部 · 明暗压成三档 | ✅ 迁移（这是风格本体） |

连带三条修正（原先写错了）：

1. **基准图那 10 个色值（`#F2EBED`…`#635B70`）不再是迁移目标**——它们只作为"饱和度水平只有 0.085"的
   **描述性证据**。prompt 里不再出现这些 hex，也不要求画面往灰紫靠。
2. **"暗部用灰紫、高光用纸白"也是色相决定**，不能强加——改为**从每个元素自己的颜色派生**：
   暗部 = 该元素自己的色相压暗去饱和，高光 = 该元素自己的色相提亮。
3. **腮红不写死 `#F4D7DA`**，改为"用目标图肤色自身派生的柔粉色低透明度晕染"。

### 铁律 B · 方案一（保构图）

只迁移渲染手法，**保留目标图的构图、人物与背景结构**。

### 其余属于"内容/构图"的项，一律不迁移

| 候选风格项 | 性质 | 说明 |
|---|---|---|
| 水彩淡涂 + 铅笔断线 + 高调低对比 + 无黑 | **纯风格** | 无条件迁移，这是核心 |
| 纯白纸底 + 40%+ 留白 | **半风格** | 它同时改变了目标图的背景内容 |
| 3:4 竖幅、单人半身胸像、居中 | **偏内容** | 会强制重排目标图的构图 |
| 抱书本 / 扶手 / 圆框眼镜 / 水手服 | **内容** | 目标图里没有就不能加 |
| 银灰或墨色长发、眼下小痣 | **人物专属** | 绝不能迁移，会改掉目标角色的身份 |

**✅ 已选定：方案一** —— 只迁移"纯风格"那一行 + 留白倾向，**保留目标图的构图、人物、背景结构**。

选了方案一意味着三件事，写 prompt 和验收时都要跟着改：

1. **不写 3:4 / 单人 / 半身 / 居中 / 抱书** —— 那些是构图与内容，写了就会重排目标图。
2. **"纯白背景"改成"简化并提亮背景"** —— 留白是这套风格最硬的判别特征（42.5%），但方案一不能换掉目标图的背景，
   只能把它**去细节、去饱和、提亮、概括化**，近似出"空气感"。这条是方案一的必然折中。
3. **"无黑 / 抬暗部"是风格核心，必然与目标图的暗部冲突** —— 见下方子取舍。

### 方案一下还有一个子取舍（我按 1A 写，要换说一声）

| | 做法 | 代价 |
|---|---|---|
| **1A 全风格（默认，下面 prompt 用这档）** | 把目标图的暗部整体抬到明度 ≥0.35，画面里不留黑 | 目标图原本的体积感与厚重感会明显变平 |
| **1B 半风格** | 只换笔触与线稿，不压饱和度、不抬暗部，保留目标图原有色彩与明暗结构 | 达标线里"亮度 P05 ≥0.35""无黑""饱和度 0.08"要全部放弃，风格更像"只换了笔触" |

依据：13 张全组的**最暗像素只有 0.166–0.320**，暗部下限是这套风格识别度最高的特征之一
（另一张异风格参考图的 P05 是 0.291、纯白占比 0.006，见主报告 10.2）。所以默认选 1A。

> **1B 什么时候用**：目标图本身是彩色饱满的作品、你要保留它的色彩语言时。1B 下 prompt 只保留
> 线稿/笔触/水彩渗染/柔边/选择性细节那几句，删掉全部饱和度与明暗的句子。要 1B 说一声。

> 方案二（连构图一起迁移成"白底单人半身"）已降级为附录，见文末。下面是方案一的 prompt。

---

## 1. A 段 · 风格解构（精简）

- **媒介与技法**：数字插画模拟传统媒材——淡水彩洗笔 + 彩铅/铅笔草稿线。非 3D、非厚涂、非赛璐璐平涂。
  依据：内容像素中 72% 属极浅近中性着色（S<0.12），色块边界渗染无硬边。
- **笔触与边缘**：断续的铅笔细线，粗细变化、收笔出锋、叠线重描，轮廓不闭合；色块轻微溢出线外，带扫笔擦痕。
  依据：13/13 张可见；线稿最暗处仅 `#4E455A`~`#74716F`，**无纯黑线**。
- **色彩处理手法**（实测——注意这是**手法指标**，不是配色目标）：
  - 主体饱和度 **0.085**（P90 仅 0.140）、明度 0.744、对比跨度 0.471 —— 迁移的是**这个水平**，不是具体色相
  - 明暗压成三档、暗部下限抬高到明度 0.35 以上、画面无黑
  - 基准图的 10 个色值（纸白 `#F2EBED` 14.1% · `#E3DEE3` 12.8% · `#D5CFD6` 11.4% · `#C3BFC3` 10.6%
    · `#B3B0B7` 10.1% · `#A3A0AB` 10.5% · `#9190A1` 10.1% · `#857F93` 8.9% · `#787084` 7.3% · 最深 `#635B70` 4.1%）
    —— ❌ **仅作描述性证据，不是迁移目标**（铁律 A）。它们只是"饱和度 0.085"这件事的外观表现。
  - 腮红在基准图里是 `#F4D7DA`（S 0.10–0.15）—— 迁移的是"**低透明度柔粉晕染**"这个手法，
    色相改为**从目标图自身的肤色派生**
  - 基准图全画唯一的高饱和暖色是占画布 <1.5% 的单件道具（红电话 / 草莓）—— 迁移的是
    "**整幅低饱和里只留一个小面积高饱和点**"这个手法，点在哪件道具上由目标图自己决定
- **光影**：正面偏上方柔和散射光，光质极软。**无落地投影、无硬边阴影、无体积光**。明暗只有三档，
  最暗处不低于明度 0.35——全组亮度 <0.20 的像素占比 0.0001%。
  **暗部与高光的色相不迁移**：改为从每个元素自己的颜色派生（见铁律 A 第 2 条）。
- **质感**：线稿稀疏（Sobel 梯度均值 2.89，区间 1.99–3.58），边缘柔，无噪点、无颗粒、无贴图纹理。
- **景深与镜头感**：无景深、无透视、无虚化，层次只靠线稿遮挡与淡色叠压。
- **细节密度**：选择性细致——碎发与睫毛密集，衣料与背景概括。
- **风格归属**：日系动漫插画 / 水彩彩铅手绘少女立绘。具体作者与作品系列未识别（依据不足，不作专名归属）。
- **情绪**：安静、温柔、内敛、略带忧郁的书卷气。
- **不可迁移项**：**所有固有色相**（目标图头发是什么颜色就保持什么颜色，不因基准图而改变）、
  银灰/墨色/蓝紫长发、蓬松碎发造型、眼下小痣与雀斑、抱笔记本与扶手动作、圆框眼镜、水手服/针织毛衣/西装、
  3:4 单人半身居中构图、纯白纸底、基准图的 10 色色板、以及画面左下/右下的**作者署名水印**（不得复制，避免伪造他人署名）。

## 2. B 段 · 可迁移风格标签（英文，权重降序）

> 已按铁律 A 改写：删掉了"muted palette"这类可能被读成"换成灰调配色"的表述，
> 改为明确的**手法**描述；`paper-white highlights` / `mid-gray shadow` 也改成**从自身色相派生**的写法。

```
1. japanese anime illustration with traditional watercolor and colored pencil media
2. soft delicate pencil sketch lineart
3. broken intermittent tapered linework with overlapping resketch strokes
4. faint watercolor wash with soft bleeding color edges
5. visible brush sweep texture, highlights made by lightening each element's own hue
6. flat soft diffuse frontal top light
7. no black, no cast shadow, lifted mid-tone deepest shadow
8. very low contrast, tonal range compressed to three flat steps
9. saturation reduced to a very low level while preserving every element's original hue
10. simplified lightened background with generous negative space
11. selective fine detailing at eyes and hair strands
12. quiet gentle melancholic literary mood, high-key and airy
```

## 3. C / E 段 · 负向标签（仅当接口有独立负向入口时用；否则改写进正文）

> **方案一专用修正**：常规的风格负向里会写 `detailed background, scenery, room, gradient background` 之类，
> 在这套风格里是错的——**负向无法区分"不要新增"和"删掉已有的"**，写进去会把目标图自己的背景一起抹掉。
> 因此下面这版**已剔除所有针对背景的负向词**，背景的处理只靠第 4 节正向段里的 `BACKGROUND` 从句完成。

```
black, pure black, deep shadow, harsh shadow, cast shadow, drop shadow, dramatic lighting,
high contrast, over-saturated, vivid colors, neon, rainbow gradient,
3d render, cgi, thick impasto, heavy brushstrokes, cel shading, flat hard-edged color blocks,
clean perfect closed lineart, vector linework,
hue shift, recolouring, palette swap, wrong hair colour, colour cast toward grey-violet or
blue-grey, monochrome conversion, full greyscale,
watermark, signature, text, logo, extra fingers, deformed hands, bad anatomy,
blurry, lowres, jpeg artifacts, noise, dirty gray, muddy colors
```

> `hue shift / recolouring / palette swap / wrong hair colour / colour cast toward grey-violet or blue-grey`
> 这五个词是**铁律 A 的负向守卫**，缺了它们模型很容易顺手把目标图的发色换成基准图的银灰或灰紫。
> `monochrome conversion / full greyscale` 防的是另一个方向的翻车：把「低饱和」执行成「去色变黑白」。

## 4. D′ 段 · 自然语言版正向 prompt（推荐，适配 GPT-Image / Kontext / 即梦 类接口）

> 双段式结构：`PRESERVE` 段锁内容身份，`STYLE` 段只讲渲染。**风格段务必保持短**——
> 上次的教训是风格段越长，模型越会顺手把内容一起重画。

```
Use the second image as the only content source, and the first image ONLY as a rendering-style
reference. Ignore all subject matter, characters, hairstyles, clothing, props AND all colours of
the first image.

PRESERVE EXACTLY from the second image: the same character identity, same face and facial
features, same expression, same pose, same framing and crop, same hairstyle, same clothing, same
accessories, and the same background structure and composition. This is a style transfer of an
existing image, not a redesign. Do not reinterpret, simplify or restyle any character, garment,
accessory or background element.

COLOUR IDENTITY LOCK — the second image keeps its own colours. Apply the colour rendering
described below as a technique only; never adopt any specific hue, colour or palette from the
first image. Keep the original hue of every element exactly as it is in the second image:
keep the hair its own colour (if it is yellow, it stays yellow — do not make it red, silver,
grey or any colour taken from the first image), keep the eye colour, keep the skin tone, keep
every garment and prop the colour it already is, and keep the background's own hue family.
Do not recolour, do not swap palettes, do not introduce the first image's palette. Shadows and
highlights must be derived from each element's OWN colour (its own hue, just lighter or
darker and less saturated), not replaced by any fixed grey, violet or blue.

STYLE TO APPLY — technique only, no palette:
japanese anime illustration rendered in traditional watercolor and colored pencil media.
Soft delicate pencil sketch lineart, broken and intermittent, with varied line weight, tapered
stroke ends and overlapping resketch strokes; contours stay slightly open and unfinished.
Colouring is a faint watercolor wash with soft bleeding edges that slightly overflow the lineart,
plus visible brush sweep marks, and highlights made by lightening the element's own hue rather
than by adding white. Lighting is a flat soft diffuse light from the front and slightly above;
no cast shadows, no hard shadow edges, no rim light, no bloom. The tonal range is compressed to
roughly three flat steps: light, mid and a lifted dark. Tone down the overall saturation to a
very low level (target roughly 0.08 average in the content area) and keep the overall value high
and bright with very low contrast. There is NO black anywhere in the image: lift the darkest
tones up to about mid-value and render them in each element's own desaturated shadow colour.
Skin gets a very soft low-opacity blush in a tone derived from the skin's own colour. Positive
and negative space stay airy. Edges stay soft, never crisp or glossy; no grain, no film texture,
no canvas texture. Detail selectively: fine strands and eyelashes rendered delicately, fabric
and surroundings kept simple and summarised.

MOOD: quiet, gentle, introspective, slightly wistful and literary. Airy and light, never heavy
or dark.

BACKGROUND (方案一，保留目标图背景结构): keep the existing background composition and all
elements that are already there, but render it much more simply and much lighter — reduce detail
density, summarise shapes, bring its saturation down to the same low level as the figure while
keeping its own hue family, lift its values so that no area of it goes dark, and let more of it
read as empty light space. Do not replace, relocate or delete background elements, do not change
the background's hue family, and do not add any new environment element.

DO NOT INCLUDE: 3D rendering, CGI, thick impasto oil painting, cel shading, flat hard-edged
colour blocks, clean closed vector linework, black outlines, deep or dramatic shadows, saturated
or neon colours, hue shift, recolouring, palette swap, colour grading toward grey-violet or
blue-grey, bokeh, sparkles, particles, paper or film grain, watermark, signature, text.
```

## 5. D 段 · 标签版正向 prompt（给 SD / Flux / NovelAI）

```
masterpiece, best quality, japanese anime illustration, traditional watercolor and colored
pencil media, hand-drawn texture, soft delicate pencil sketch lineart, broken intermittent
linework, varied line weight, tapered stroke ends, overlapping resketch strokes, unclosed
contours, faint watercolor wash, soft bleeding color edges, color slightly overflowing lineart,
visible brush sweep marks, highlights made by lightening each element's own hue,
low saturation with every element's original hue preserved, high-key, airy, bright,
very low contrast, tonal range compressed to three flat steps,
flat soft diffuse frontal top light, no black, no deep shadow, lifted mid-tone darkest shadow,
soft edges, selective fine detailing, simplified lightened background, generous negative space,
quiet gentle introspective wistful literary mood
```

## 6. F 段 · 参数建议

**F1 分支 A — 你现在的 edits 类接口（gpt-image-1 / Kontext 之类，参考图 + 目标图 + 文本）**
- 接口：`/v1/images/edits`，或插件里上传两张图 + 文本。
- **上传顺序必须在文本里点名**（上面写的是 "the second image as content / the first image as style"，若插件顺序不固定，
  改成显式命名："the girl holding the notebook is the style donor; the other image is the content"）。
- `size`：跟随**目标图**比例，不要用 3:4（那是风格图的比例，用错会重排构图）。
- `quality=high`，`n=1` 起步，最多 2–4 张选优。
- `denoise / CFG / steps / sampler / mask`：**在这类接口上不适用**，别去填。
- 负向：无独立入口 → 用上面正文里的 `DO NOT INCLUDE` 段替代。
- **重跑顺序**：① 先跑 2 张 → ② 若"手绘笔触"不够，把 `STYLE` 段前两句提到最前面并加重 → ③ 若身份漂移
  （发色/配件/构图变了），缩短 `STYLE` 段、把 `PRESERVE` 段移到第一句，并补一句"do not reinterpret"。



**F3 分支 C — 纯文生图（无目标图，从零生成同风格图）**
- 直接用 `style_prompt.md` 第 1 节中文版或第 2 节英文版，尺寸 1200×1600。

## 7. G 段 · 自检与已知风险

1. **身份漂移（最高风险）**：如果目标图与这 13 张的人物先验重合（例如目标图也是"浅发色少女半身像"），
   模型会收敛到两者的公共先验，产出一个"平均像"——**既不像目标图，也不像风格图**。上次就是这样翻车的。
   判据：改完先盯三处——发色是否被漂白/漂灰、配件是否被简化或位移、肩线与头颈角度是否被摆正。
2. **负向通道缺失**：无负向入口时，`DO NOT INCLUDE` 段落必须留，删了它黑色和脏灰会回来。
3. **这个冲突已按 1A 处理**：这 13 张是"低对比 + 高调"，而多数目标图（尤其照片、厚涂插画）本身带重阴影。
   prompt 里的 `no black / deepest tone is grey-violet / three flat steps` 会**必然削弱**目标图的体积感。
   这是选 1A 换来的代价，不是 bug。若某张目标图你更看重立体感，改走 1B（见第 0 节），并同步放弃"无黑"达标线。
4. **素材边界**：这 13 张有作者署名水印，是他人作品。做同风格迁移可以，**不要复刻署名**，也不要把这组图当作自己作品的原创素材。
5. **验收（方案一版）**：把输出图丢进验证脚本对照指标，比肉眼可靠：
   ```
   python style-distill/analyze_style.py <输出图所在目录> -o style-distill/new_stats.json
   ```
   达标线：
   - **最暗像素明度 ≥0.15 · 亮度 P05 ≥0.35**（方案一的核心——抬暗部、不留黑）
   - **内容明度均值 ≥0.60**
   - 背景已被简化提亮：背景区域的饱和度与细节密度明显低于目标图原图
   - ❌ **不要**拿"纯白(>0.97)占比 ≥0.35"验收——那是方案二的线，方案一保背景结构，这条必然不达标
   - ❌ **不要**拿"内容饱和度 ≤0.15"或 b\* 色温验收——实测无判别力（异风格图 0.077 夹在本风格 0.035 与 0.144 之间）

   > 实测对照（同一脚本）：异风格图 `compose/style_ref.png` 的纯白占比 0.006、亮度 P05 0.291；
   > 本风格两张为 0.503/0.579 与 0.520/0.387。**只有留白占比与最暗值下限能拉开差距。**

---

## 8. 色相保证 · 后处理（铁律 A 的物理兜底）

光靠提示词守不住铁律 A——上次的教训就是纯文本约束有上限，模型会顺手把目标图的发色换成
基准图色板里的银灰/灰紫。所以加一道**像素级后处理**：`preserve_hue.py`

```
python style-distill/preserve_hue.py --style-output <生成图> --original <原目标图> -o <输出> \
    [--sat-scale 1.0] [--chroma-blur 0]
```

**它做什么**：把两个来源拆开重组，在 CIE Lab 里

| 通道 | 取自 | 效果 |
|---|---|---|
| **L**（明暗结构、光影） | **生成图** | 拿到水彩笔触、高调、无黑的明暗处理 |
| **h**（色相） | **原图** | **黄发保持黄发，红发保持红发，不受基准图影响** |
| **C**（彩度） | 原图 × `sat-scale` | 色相方向不动，只缩放浓淡 |

**关键取舍**：`sat-scale` 默认 **1.0 = 完全保留原图饱和度**，这是最贴合"不换配色"的档位。
若你要同时拿到 1A 的低饱和手法，把它调小——脚本会算出该给多少（例：原图饱和度 0.105 时，
压到风格水平 0.085 需要 `--sat-scale 0.81`）。**这一步是你唯一需要决定"风格手法要不要盖过原图色彩"的地方。**

**已验证**：
- Lab 往返 `--selftest` 精确（偏差 0.0000/255）
- 恒等测试：同一张图作输入输出，**最大像素差 0/255、100% 像素完全相同、色相偏差 0.00°** → 色彩零损失

**已知限制（实测踩到，务必注意）**：色相取自原图的**同位置**像素。如果生成图与原图**几何有位移**，
色相会整体错位——我用 `78A4`（藏青外套 + 红电话）的色彩套到 `1A37`（鼠尾草）的明暗结构上试过，
那部红电话的红色**错位糊到了下巴和手臂上**。所以：

1. 生成图与原图几何越接近，这一步越干净。方案一 + ControlNet 结构锁（denoise 0.35–0.5）时几何吻合度高，直接可用。
2. 若几何有位移，调大 `--chroma-blur`（建议 3–8 px）把色相低通，代价是边缘色彩变柔。
3. 位移很大时（例如 gpt-image-1 重排过构图），**这一步不适用**，只能靠提示词 + 人工挑图。

---

## 附录 · 方案二（连构图一起迁移）— 已降级，仅在目标图本身就是人物立绘时用

把第 4 节 `D′` prompt 里的 `BACKGROUND (方案一…)` 段整段替换成下面这段，其余不动：

```
BACKGROUND: replace the background with a clean blank paper-white field, keeping only a few
summarised graphic shapes from the original composition. Increase the amount of empty white
space to over 40 percent of the canvas, with the figure centred and cropped as a bust portrait,
generous white space around the silhouette, and no environmental detail. Do not add any prop,
hairstyle, accessory or garment that comes from the first image.
```

同时把输出尺寸改为 **1200×1600（3:4）**，并把第 7 节验收线换成方案二的：
纯白占比 ≥0.35 · 内容明度 ≥0.60 · 亮度 P05 ≥0.35 · 3:4 单人半身居中。

**注意**：方案二会**重排目标图**，人物位置、裁切、手与道具全部会被改成这套风格的模样——
只在目标图本身已经是"单人立绘"时才成立，否则等于把目标图的内容丢掉一半。
