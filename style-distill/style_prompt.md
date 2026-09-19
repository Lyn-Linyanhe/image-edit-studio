# 风格提示词（可直接粘贴使用）

配套文档：`漫画风格蒸馏.md`（拆解依据）、`style_card.json`（结构化数据）。

---

## 1. 中文提示词 · 自然语言版
> 适用：GPT-Image / 即梦 / Seedream / 豆包 等中文自然语言模型。整段直接粘贴。

```
日系动漫插画，少女半身胸像，模拟水彩与彩铅的手绘纸质感。

风格：数字作画但模仿传统媒材——铅笔草稿线与淡水彩晕染结合。轮廓线断续、有粗细变化和收笔出锋，
局部叠线重描，线稿不闭合，保留明显草稿感。上色为极淡的水彩洗笔，色块边界模糊、渗染并偶尔溢出线外，
可见扫笔与擦痕。没有厚涂、没有赛璐璐平涂硬边、没有 3D 渲染。

主体：一名 16-24 岁的年轻女性，学生或白领气质。蓬松凌乱的长发，碎发飞扬、发梢外翻，
低饱和灰调发色（银灰 / 灰紫 / 墨灰 / 蓝紫中选一，绝不能是黑发或鲜艳染发）。
大眼睛，浓密分束的上翘睫毛，瞳孔有渐变与细小的星状高光，眼白面积小，眼型微下垂。
脸颊有大面积的极柔奶粉色腮红，眼下带一两颗小痣或雀斑。
穿素色针织高领毛衣 / oversize 开衫 / 白衬衫 / 西装外套，无印花无图案。

动作与道具：双手抱着一本笔记本或文件夹夹在胸前，或手扶眼镜框、手托腮、铅笔抵着下巴。
道具为文具与日常物：笔记本、文件夹、信封、铅笔、圆框眼镜、复古拨号电话、蛋糕、棒棒糖。
手部必须出现在画面内，和道具一起构成胸前的三角结构。

构图：3:4 竖幅，单人，半身胸像，主体绝对居中，脸部位于画幅上半部中央偏上。
头部倾角 10-20 度，肩线倾斜，接近平视但绝不正面平脸。头顶距上缘约 5%，下缘裁切在腰部。
视线落在画外或与观者对视，表情安静内敛。
背景是纯白纸底，什么都没有——没有房间、没有家具、没有渐变背景、没有色块、没有光斑粒子。

色彩：极低饱和度（内容区域平均饱和度 0.08 左右），高调偏亮，低对比。
色板是一条从纸白到深灰紫的连续灰阶：
#F2EBED、#E3DEE3、#D5CFD6、#C3BFC3、#B3B0B7、#A3A0AB、#9190A1、#857F93、#787084、#635B70。
可选配色分支：鼠尾草米白（#F0E9E6 / #BAB7B2 / #9FA09B）、薰衣草灰紫（#E4DAE7 / #A89DBA / #6A607F）、
藏青石墨（#E5E5F0 / #ABACBB / #696775）。
唯一的暖色是一个占画面不到 1% 的小道具（红色电话、一颗草莓），
腮红用 #F4D7DA 这样饱和度仅 0.1 的奶粉色。

光影：正面偏上方的柔和散射光，光质极软。没有硬边投影、没有落地影子、
没有镜面高光、没有体积光与光晕。明暗只有"白 / 浅灰 / 中灰"三层，
暗部最深处相当于 #635B70 的明度，画面里不出现黑色和深阴影。
头发高光用留白和浅色笔触提亮，呈丝状洗笔痕。

氛围：安静、温柔、内敛，带一点忧郁与眷恋的书卷气。留白占画面 40% 以上，空气感强。
```

**负向（中文）**：
```
黑色，纯黑头发，深阴影，重阴影，落地投影，高对比，鲜艳饱和的色彩，荧光色，渐变色大色块，
复杂背景，房间，风景，虚化背景，光斑，粒子，纹理贴纸，3D 渲染，厚涂，油画厚笔触，
赛璐璐平涂硬边，干净闭合的完美线稿，无草稿感的电脑描线，双人，群像，全身像，横构图，
性感化，暴露，浓妆，成人向，塑料质感，金属反光，水印，签名，文字，logo，畸形手指，
多余手指，脸崩，眼睛不对称，低分辨率，模糊，脏灰，噪点
```

---

## 2. 英文 tag 版
> 适用：SDXL / Flux / NovelAI / ComfyUI。权重语法按你的前端调整。
>
> ⚠️ **第 1 节与第 2 节都是「文生图」用**（从零造一张同风格的新图）——**这种情况下写死基准图色板是对的**。
> 但**做改图（第 3 节）时绝不能带这里的色板 tag**：写进去模型就会把目标图的黄发换成银灰、
> 把目标图的配色换成灰紫。改图请用第 3 节，那里已按铁律 A 剔除全部配色 tag。

**正向**
```
masterpiece, best quality, anime illustration, manga style, japanese light novel illustration,
watercolor and colored pencil on paper, traditional media imitation, hand-drawn texture,
soft delicate pencil sketch lineart, broken intermittent outlines, varied line weight,
tapered stroke ends, overlapping resketched lines, unclosed contour lines,
loose sketchy finish, faint watercolor wash, soft bleeding color edges, color slightly
overflowing the lineart, visible brush sweep marks,

1girl, solo, upper body, bust portrait, centered composition,
messy voluminous long hair, fluffy tousled hair, loose flyaway strands, wispy hair strands,
silver gray hair, ash purple hair, muted smoky gray hair, low saturation hair color,
large eyes, thick separated eyelashes, gradient iris with tiny star-shaped highlight,
small sclera, downturned gentle eyes, soft pink blush, tiny mole under eye, faint freckles,
neutral color oversized knit turtleneck sweater, white shirt, blazer, plain unpatterned clothing,
holding a notebook against her chest, holding a folder, hand adjusting round glasses,
hand on cheek, chin resting on hand, pencil touching chin,
notebook, folder, envelope, pencil, round-frame glasses, retro rotary phone, strawberry cake, lollipop,
hands visible in frame,

plain white paper background, pure white background, empty background, no background,
huge negative space, minimalist,
3:4 vertical aspect ratio, head tilted, slanted shoulders, looking away, looking off-screen,
quiet gentle melancholic expression, wistful,

desaturated, extremely low saturation, muted color palette, high key, bright airy,
soft low contrast, no black, no deep shadow, flat soft diffuse lighting, soft frontal top light,
paper white highlights, silky hair highlight strokes, pastel gray purple palette,
sage green palette, dusty lavender palette, navy graphite palette,
very pale milk pink blush, single small warm accent prop,

paper grain, gentle, serene, literary mood, soft atmosphere
```

**负向**
> ⚠️ 这组负向是给**文生图**用的（复刻参考图的纯白背景）。**做「方案一」改图时不要照搬**——
> 其中的 `detailed background, scenery, room, gradient background` 会把目标图自己的背景一起删掉。
> 方案一请用 `img2img_方案.md` 第 3 节那版已剔除背景词的负向。
```
black, pure black hair, deep shadow, harsh shadow, dramatic lighting, cast shadow, drop shadow,
high contrast, over-saturated, vivid colors, neon, fluorescent, rainbow, gradient background,
detailed background, scenery, room, furniture, bokeh, lens flare, light particles, sparkles,
3d render, octane render, unreal engine, cgi, thick impasto oil painting, heavy brush strokes,
cel shading, flat hard-edged color blocks, clean perfect closed lineart, vector lineart,
2girls, multiple girls, group, full body, wide shot, horizontal composition,
nsfw, sexualized, revealing clothes, heavy makeup, realistic photo, plastic skin, glossy metal,
watermark, signature, text, logo, bad hands, extra fingers, missing fingers,
bad anatomy, deformed face, asymmetric eyes, low quality, blurry, jpeg artifacts, noise, dirty gray
```

---

## 3. 改图指令模板（把已有图片改成这一风格）

### 3.1 给支持「参考图 + 指令」的模型（GPT-Image / 即梦 / Seedream / Nano Banana）

> **铁律 A 已内置**：下面这版**只迁移手法、不迁移配色**。原图头发是什么颜色就保持什么颜色，
> 不会因为基准图是银灰/红/紫而改变。**没有出现任何基准图的 hex 色值**——这是故意的。
```
保持这张图的人物姿态、身份、五官、发型发色、服装、道具、构图、背景结构全部不变。
这是一次风格迁移，不是重新设计。不要重新诠释、简化或改变任何一个角色特征、服饰或背景元素。

只把画法改成下面这一种（只改手法，不改颜色）：

改造成水彩与彩铅手绘质感的日系动漫插画。轮廓线改成断断续续的铅笔草稿线，
有粗细变化和收笔出锋，允许叠线重描，线稿不必闭合。上色改成极淡的水彩洗笔，
色块边界要模糊渗染、允许轻微溢出线外，并保留扫笔擦痕。边缘保持柔，不要锐利、不要塑料光泽。

颜色规则（最重要）：
这张图里每个元素自己的颜色一律保持原样——头发的颜色、眼睛的颜色、肤色、每件衣物和道具的颜色、
背景的色相族，全部不变。不要换成别的颜色，不要做调色板替换，不要把画面往灰紫或蓝灰上靠。
明暗和暗部要从每个元素自己的颜色派生（该元素自己的色相压暗、降饱和），
高光也从该元素自己的色相提亮，不要统一换成灰紫或纸白。

只改色彩处理强度，不改色相：把整体饱和度压到很低（内容区域平均约 0.08），
明度整体抬高，对比度压低，明暗关系压成三档。
画面里不要出现黑色和深阴影——最暗处抬到中等明度，用该元素自身色相的暗色表现，不要用纯黑。
皮肤上的腮红用柔和低透明度晕染，色调从肤色自身派生即可。

光影改成正面偏上方的柔和散射光，去掉投影和硬边阴影，不要体积光和光晕。

背景保留原有的构图和元素，但要做简化与提亮：去掉细碎细节、把形状概括化、
色相族保持不变、整体提亮到不出现暗块，并让更多区域读作浅色空场。
不要替换、挪动或删除背景里已有的元素，也不要新增环境元素。

最终氛围是安静、温柔、内敛、带书卷气的插画。
不要 3D 渲染、不要厚涂、不要赛璐璐平涂、不要换色、不要调色板替换、不要改成黑白或全灰。
（若你要的是"连构图一起换成白底单人半身"，见 `img2img_方案.md` 文末的方案二附录。）
```

### 3.2 ComfyUI / SD 图生图参数配方
见 `漫画风格蒸馏.md` 第 10.1 节。要点复述：

| 输入类型 | Denoise | ControlNet | CFG |
|---|---|---|---|
| 已是插画/线稿，只换味道 | 0.35–0.50 | lineart 或 softedge，权重 0.6–0.8 | 5–6 |
| 照片 / 写实图 | 0.55–0.75 | softedge，权重 0.5–0.7 | 5–7 |
| 想大幅重画 | 0.75–0.85 | 视需要，可不用 | 6–7 |

- 风格锁定优先用 **IPAdapter（权重 0.6–0.8）** 或训练一个风格 LoRA，光靠提示词很难压住低饱和高调这个特征。
- 采样器建议 DPM++ 2M / Euler a，步数 25–35，**不要开高 CFG**（会把对比度拉回来）。
- 若输出偏脏偏灰，先检查是不是负向提示词缺了 `dirty gray`、`noise`，以及 CFG 是否过高。
