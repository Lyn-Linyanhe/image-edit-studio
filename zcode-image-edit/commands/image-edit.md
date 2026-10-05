---
description: 改一张图：圈定区域（或整图）→ 调图生图接口，只改那一块
argument-hint: "[要改成什么样]（可一并给出图片路径与区域，如 --rect 100,200,600,900）"
skills: image-edit
---

用 `image-edit` 技能作为执行层完成这次改图。AI 先解析用户意图、输入图角色和任务类型，再决定是否需要 `style-distill` 编译提示词。用户的意图：

$ARGUMENTS

默认由 AI/CLI 完成，不打开网页；网页只在复杂区域无法用 `--rect/--polygon/--flood/--grabcut` 表达且确实需要手涂时使用。按下面的顺序做，**不要跳步**：

1. 先跑自检：`C:\Python314\python.exe zcode-image-edit\bin\zimage.py doctor`。
   若报 `RELAY_API_KEY` 未设置，**停下来**把设置方法告诉用户（PowerShell 的 `$env:` 写法），
   并说明"只想看预算的话可以加 `--dry-run`"。
2. 确认输入图路径与要改的区域。区域四选一：`--rect x0,y0,x1,y1` / `--polygon "x,y x,y x,y"` /
   `--flood x,y[,tol]`（"把这片背景换掉"最趁手）/ `--grabcut`；整图改则用 `--whole`；
   要保护的语义用 `--protect`。**没有把握先问用户**，不要猜坐标。
3. **先 `--dry-run`**：它会打印区域占比、投喂 MiB、是否触发压缩、预计结果体积与取回时间三档，**不发送**。
   把这张报表**念给用户听**（尤其"可改面积 %"和"最坏取回时间"），并告诉用户涂红图落在
   `<out>.redmark.png`，请他确认红色位置对不对。
4. 用户确认后再去掉 `--dry-run` 真跑。正向改图默认自带 `--mask-primary`，**不要**擅自加 `--no-primary`。
5. 跑完报结果：路径、尺寸、字节，并说明末尾已做过完整解码校验。
   若结果偏色或改错地方，不要反复重跑——按 `style-distill` 技能的升级规则处理。

约束：不要把 API Key 写进任何文件或命令行参数（只从环境变量读）。
不要用肉眼下结论；能出数的用 `local tone-report` 之类的命令出数。
