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
| `prompt_masktest.txt` | 第 1 次正向蒙版测试（要求画的内容与现状相同 → 设计失误） | `out_masktest_1k.png` |
| `prompt_masktest2.txt` | 第 2–4 次正向测试（要求纯黑蝴蝶结；蒙版先在天空、后在头发） | `out_masktest2_1k.png`、`out_masktest3_1k.png` |
| `prompt_masktest3.txt` | 极简提示词（只留正向） | `out_masktest4_1k.png` |
| `prompt_masktest4.txt` | 明确禁止"复原原内容"（R5 三次实验也用它） | `out_masktest6_norestore.png`、`out_r5a_pad.png`、`out_r5b_big.png`、`out_r5c_primary.png` |
| `prompt_maskinvert.txt` | 反向蒙版（涂哪保哪）：整体改成黄昏雪景、保护区＝眼与脸颊 | `out_maskinvert_1k.png` |
| `run_r5_matrix.ps1` | R5 实验矩阵（pad / 大区域 / 只发涂红图）的可复跑脚本 | `out_r5*.png` |

**目录约定**：本目录放实验件——提示词 + 实验输出 + 复跑脚本。
`round_snow/` 顶层只保留**交付件**（`out_A1_1k.png`、`out_B1_1536x1024.png`），
这条由验收套件 C3 机械检查（顶层 PNG 只能是交付件）。

**注意**：`../round_lib/pending_urls.json` 里这些文件仍记在 `round_snow/` 顶层——
那是**下载当时的原样记录**（时间戳台账），事后移文件不回头改台账，以免把证据改成"现在看起来对"的样子。

结论见 `../../验收_局部改图与工具链_2026-09-22.md`：**正向蒙版 6 次调用均未产生局部编辑；
反向蒙版的保护有效，但保护区是原像素硬贴（整体换色时会留下硬边色块）。**
