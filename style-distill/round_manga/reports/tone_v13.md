# v13 调子验收表

基准 = `out_v12C.png`（用户认为"淡然"的那一版）。
判读：**深** = 墨量高、灰调高、纸白低、平均亮度低、对比跨度大。

## 指标

| 文件 | 纸白 | 墨量 | 灰调 | 亮部 | 平均亮度 | 对比跨度 | 彩度 | 与基准距离 |
|---|---|---|---|---|---|---|---|---|
| out_v13_1.png | 0.647 | 0.040 | 0.163 | 0.798 | 0.884 | 0.576 | 0.4 | **0.074** |
| out_v13_2.png | 0.631 | 0.048 | 0.174 | 0.778 | 0.872 | 0.639 | 0.4 | 0.113 |
| out_v13_3.png | 0.671 | 0.032 | 0.137 | 0.830 | 0.900 | 0.516 | 0.4 | 0.193 |
| out_v12B.png（改前） | 0.604 | 0.061 | 0.232 | 0.707 | 0.842 | 0.698 | 0.5 | 0.360 |
| out_v12C.png（基准） | 0.670 | 0.040 | 0.179 | 0.780 | 0.881 | 0.590 | 0.5 | 0.000 |

## 计划里定的验收线

| 指标 | 阈值 | v13_1 | v13_2 | v13_3 |
|---|---|---|---|---|
| 纸白 ≥ 0.660 | | 0.647 ✗ | 0.631 ✗ | 0.671 ✓ |
| 灰调 ≤ 0.185 | | 0.163 ✓ | 0.174 ✓ | 0.137 ✓ |
| 墨量 ≤ 0.045 | | 0.040 ✓ | 0.048 ✗ | 0.032 ✓ |
| 平均亮度 ≥ 0.875 | | 0.884 ✓ | 0.872 ✗ | 0.900 ✓ |
| 对比跨度 ≤ 0.610 | | 0.576 ✓ | 0.639 ✗ | 0.516 ✓ |
| **合计** | | **4/5** | **2/5** | **5/5** |

## 两种判读口径的差异（重要）

- **按"与基准 C 的距离"**：`v13_1`（0.074）最接近。
- **按计划定的阈值**：`v13_3`（5/5）全达标。

两者不一致的原因：`v13_3` 在"更淡"的方向上**越过了 C**——灰调 0.137（C 是 0.179）、纸白 0.671（C 0.670）、平均亮度 0.900（C 0.881）。
所以这两个口径测的其实是两件事：**"像不像 C"** vs **"够不够淡"**。

- 若你要的是"C 那种淡然"→ 选 `v13_1`（层次保留最完整）。
- 若你要的是"越淡越好，甚至比 C 更淡"→ 选 `v13_3`（但要注意层次可能偏少）。

## 共同项（三版都保住）

- 动作神态沿用 B：**张嘴笑露虎牙、一条腿屈膝抬起、双臂向两侧张开、身体扭转**
- **跳出框架**：小腿与脚越过外框下缘线、下缘线在腿处断开；其余三边完整
- 三格发型束法／头饰佩戴状态各不相同；中灰百褶短裙；背景大面积纯白
- 全程为黑白（平均彩度 0.4，已确认无彩色）

## 复现命令

```powershell
python -u style-distill/round_lib/run_round.py `
  --content style-distill/round_manga/work/feed_char_clean.png `
  --ref style-distill/round_manga/ref_xiami/R3_gray900.png `
  --prompt style-distill/round_manga/prompt_threeview_v13.txt --out style-distill/round_manga/out_v13_1.png `
  --prompt style-distill/round_manga/prompt_threeview_v13.txt --out style-distill/round_manga/out_v13_2.png `
  --prompt style-distill/round_manga/prompt_threeview_v13.txt --out style-distill/round_manga/out_v13_3.png `
  --budget-mib 1.55 --concurrency 3

python -u style-distill/round_lib/tone_report.py style-distill/round_manga/out_v13_*.png `
  --ref style-distill/round_manga/out_v12C.png
```
