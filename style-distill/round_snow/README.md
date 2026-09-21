# round_snow · 雪景少女（彩色漫画稿 / 三视图）

## 交付件（留在本目录，路径保持不变）

- `out_A1_1k.png` — **雪景少女 · 彩色漫画稿（单幅，保留配色）**  `✓  2.73 MB`
- `out_B1_1536x1024.png` — **雪景少女 · 三视图＋外框＋跳出框架（彩色）**  `✓  1.89 MB`

## 其余内容的位置

- `input/` — 输入图（不可改动），3 个文件

## 顶层还有什么

```
README.md
out_A1_1k.png
out_B1_1536x1024.png
prompt_snow_A.txt
prompt_snow_B.txt
```

## 复现与工具

- 一键跑一轮：`python style-distill/round_lib/run_round.py --help`
- 开工前预算报表：加 `--dry-run`（只报表不发送）
- 确定性操作（减淡线稿/放大/裁切/拼版/调子）：`python style-distill/round_lib/local_ops.py --help`
- 补下结果：`python style-distill/round_lib/fetch_url.py --pending`
