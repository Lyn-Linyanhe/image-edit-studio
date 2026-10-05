# 身份泄漏词库与使用纪律

## 为什么需要它

参考图组如果是**同一个角色**的若干张图（很常见：一次生成批次的产物），那么把这组图当风格参考投喂时，模型会把这个角色的身份一起带进目标图。发色、瞳色、耳形、额头记号、标志性饰品都会外溢——其中**发色同时违反 R1**。

## 两条纪律（比词表本身更重要）

### 纪律一：不要把"发色词"写进负向

发色由 `wrong hair colour` 与 COLOUR LOCK 那一段守。
若把 `blonde` / `blonde hair` / `silver hair` 之类直接写进负向，会在**目标角色本来就是该发色**时把她一起抹掉，形成"正向要金、负向禁金"的两头夹。

### 纪律二：逐项条件化

列出的每一条都必须先对照目标图检查：**凡目标图本身已有的那一行必须删掉**，否则会把目标图自己的特征一起拦掉。

## 词表（按特征族分组，按实际取用）

```
颜面与耳
  pointed elf ears, elf ear shape, forehead stitch mark, forehead cross mark

饰品
  blue teardrop earrings, blue thorn circlet, star hair ornament, star charm,
  bracelet, star charm bracelet, wrist chain, thin necklace, chain necklace

服饰
  off-shoulder dress, ribbon bow, black bow, frilled sleeves, ruffled cuffs,
  high collar, round pendant, school uniform, tracksuit

笔迹与符号
  floating star symbol, gold sparkle glyph, gold cross glyph, speech bubble,
  hand-drawn glyph marks floating around the figure

背景
  purple background wash, blue background wash, gradient background wash
```

## 使用方式

在第 6 段的 DO NOT INCLUDE 里，配合一句总纲：

> 不要把参考图中的任何角色、服饰、道具或场景带进来；不要引入参考图的任何色相或调色板。

再逐条列出上面那些**目标图确实没有**的特征行。
