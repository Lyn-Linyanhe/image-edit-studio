---
description: 打开网页手涂遮罩（本地服务，与 DSH 无关），涂完再喂给改图命令
argument-hint: "[可选的端口，默认 8000]"
skills: image-edit
---

用户要用**手涂**的方式指定要改的区域（比文字圈区域更精细）。可选参数（端口）：

$ARGUMENTS

执行：

1. 拉起本地服务并打开浏览器：
   `C:\Python314\python.exe zcode-image-edit\bin\zimage.py serve`
   （指定端口就加 `--port <端口>`；不想自动开浏览器加 `--no-open`。）
2. 确认服务真的起来了：命令会打印 `GET http://127.0.0.1:8000/ → HTTP 200`。
   如果不是 200，**别猜**——让服务前台跑一次看报错：
   `C:\Python314\python.exe compose\images\mask_edit_app.py --port 8011`
3. 告诉用户怎么做：在网页里**涂出要改的区域**、填提示词、点生成；
   或者只用它**导出遮罩 PNG**，然后回头走命令行的批量/可复现路线。
   凭据已由环境变量注入服务端默认值，页面上不必再手填。
4. 用完提醒用户停止服务：`C:\Python314\python.exe zcode-image-edit\bin\zimage.py stop`

注意：网页里手填的 Key 只存浏览器 localStorage，服务端不会下发它；
**不要把 Key 抄进对话或任何文件**。
