---
description: 打开图片画廊（八分类页签＋灯箱），并先刷新「输入」页签的数据源
argument-hint: "[可选：端口]"
skills: image-edit
---

用户要看图库。可选参数（端口）：

$ARGUMENTS

执行：

1. **先刷新「输入」页签的索引**（ZCode 侧的图不存成独立文件，得从 SQLite+artifacts 重建）：
   `C:\Python314\python.exe zcode-image-edit\zcode_inputs.py`
   它会打印：本项目会话数、图片附件数、工作区参与配对的不同图片数，以及
   `paths / excluded / unreachable` 三个口径的数量。
2. 让画廊用这份索引（指向它，**不要**去改画廊的分类代码）：
   `set GALLERY_USER_INPUTS=<工作区>\style-distill\round_lib\user_inputs_zcode.json`
3. 打开画廊：
   `C:\Python314\python.exe zcode-image-edit\bin\zimage.py gallery`

关于"输入"页签报 0 条：**那是如实结果，不是故障**——本机 ZCode 的
`session_input.payload.attachments` 目前全是空数组（还没有在 ZCode 对话里发过图）。
在对话里真发一张图后重跑第 1 步即可看到。**不要为此造假卡片或编造数量。**

如果用户其实是想看某一张具体图的细节，优先用 Read 直接看那张图，
而不是开画廊——画廊的价值在"浏览与分类"，不在"看这一张"。
