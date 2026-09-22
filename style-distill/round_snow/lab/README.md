# round_snow/lab · 实验提示词

这里放**实验性**提示词，与 `../` 根层的**生产**提示词区分开。

- 根层的 `prompt_snow_A.txt` / `prompt_snow_B.txt` 是这一轮真正的作业提示词，进 `lint_prompt.py --all-rounds` 的校验范围。
- 本目录的 5 份是 `--mask` / `--mask-invert` 通道验证用的实验件，**逐字保留实际发送时的原文**
  （所以在实验结束后一个字都没有改——改了就不再是"当时发出去的那份"）。
  校验器只扫 `round_*/prompt_*.txt` 根层，因此它们不在校验范围内：
  这是**约定**，不是为了让它们躲开校验——它们确实缺 L1 负向段与 L2 取景约束，
  而局部改图的实验件不必按生产提示词的完整骨架写。

| 文件 | 用途 | 对应输出 |
|---|---|---|
| `prompt_masktest.txt` | 第 1 次正向蒙版测试（要求画的内容与现状相同 → 设计失误） | `../out_masktest_1k.png` |
| `prompt_masktest2.txt` | 第 2–4 次正向测试（要求纯黑蝴蝶结；蒙版先在天空、后在头发） | `../out_masktest2_1k.png`、`out_masktest3_1k.png` |
| `prompt_masktest3.txt` | 极简提示词（只留正向） | `../out_masktest4_1k.png` |
| `prompt_masktest4.txt` | 明确禁止"复原原内容" | `../out_masktest6_norestore.png` |
| `prompt_maskinvert.txt` | 反向蒙版（涂哪保哪）：整体改成黄昏雪景、保护区＝眼与脸颊 | `../out_maskinvert_1k.png` |

结论见 `../../验收_局部改图与工具链_2026-09-22.md`：**正向蒙版 6 次调用均未产生局部编辑；
反向蒙版的保护有效，但保护区是原像素硬贴（整体换色时会留下硬边色块）。**
