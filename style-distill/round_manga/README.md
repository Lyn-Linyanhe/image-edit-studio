# round_manga · 夏弥三视图 / 线稿减淡

## 交付件（留在本目录，路径保持不变）

- `out_C3.png` — 黑白漫画定稿（你当时评价「这张图的效果非常可以」）  `✓  2.71 MB`
- `out_color1.png` — 上色版（黑白稿 + 图1 配色，蓝色荷叶边/粉色挂件都在）  `✓  2.58 MB`
- `out_v12B.png` — 线稿减淡的基准原图（你说「其他都不用动」的那张）  `✓  1.88 MB`
- `out_v12B_lineLighter_s1.png` — **线稿减淡 · 轻档（你明确认可的就是这张）**  `✓  1.52 MB`
- `out_v12B_lineLighter_s2.png` — 线稿减淡 · 中档（备选，更淡）  `✓  1.51 MB`
- `out_v12C.png` — 「淡然」调子基准（tone_report 的 --ref 用它）  `✓  1.73 MB`
- `out_final_4k_2880.png` — 上者的本地放大 4K（2880×2880，内容一像素不差）  `✓  7.74 MB`
- `out_v16_uncompressed.png` — 2K 横 · 投喂未压缩（脸最像的一版，2048×1152）  `✓  3.66 MB`
- `out_2kL_2048x1152.png` — 2K 横 · 接口生成（身份参考 900px 清晰）  `✓  3.93 MB`
- `out_4kL_3840x2160.png` — 4K 横 · 接口生成（3840×2160，跳出框架）  `✓  9.54 MB`

## 其余内容的位置

- `checks/` — 对照图 / 掩膜预览 / 坐标网格等检查用图，23 个文件
- `input/` — 输入图（不可改动），3 个文件
- `ref_xiami/` — 你提供的夏弥参考图（R1 啦啦队 / R2 游乐园 / R3 生日，含灰度裁切），10 个文件
- `reports/` — 指标表与原始数据，3 个文件
- `scripts/` — 该轮用到的脚本，18 个文件
- `work/` — 中间生成结果（逐轮迭代版本），34 个文件

## 顶层还有什么

```
RUN.md
out_2kL_2048x1152.png
out_4kL_3840x2160.png
out_C3.png
out_color1.png
out_final_4k_2880.png
out_v12B.png
out_v12B_lineLighter_s1.png
out_v12B_lineLighter_s2.png
out_v12C.png
out_v16_uncompressed.png
prompt_A.txt
prompt_B.txt
prompt_C.txt
prompt_C2.txt
prompt_C3.txt
prompt_cn.txt
prompt_colorize.txt
prompt_threeview.txt
prompt_threeview_v10.txt
prompt_threeview_v11.txt
prompt_threeview_v12A.txt
prompt_threeview_v12B.txt
prompt_threeview_v12C.txt
prompt_threeview_v13.txt
prompt_threeview_v14.txt
prompt_threeview_v15.txt
prompt_threeview_v2.txt
prompt_threeview_v3.txt
prompt_threeview_v4.txt
prompt_threeview_v5.txt
prompt_threeview_v6.txt
prompt_threeview_v7.txt
prompt_threeview_v8.txt
prompt_threeview_v9.txt
```

## 复现与工具

- 一键跑一轮：`python style-distill/round_lib/run_round.py --help`
- 开工前预算报表：加 `--dry-run`（只报表不发送）
- 确定性操作（减淡线稿/放大/裁切/拼版/调子）：`python style-distill/round_lib/local_ops.py --help`
- 补下结果：`python style-distill/round_lib/fetch_url.py --pending`
