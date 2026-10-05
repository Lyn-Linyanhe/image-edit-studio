# 改图（image-edit）—— ZCode MCP 插件形态

本地涂抹改图：在图上画出要改的区域，经 OpenAI 兼容中转站调用 `gpt-image-*` 系列的 `/images/edits`。三栏工作台：**改图**（涂红/矩形遮罩 + 全屏对比查看器）、**生图**（清晰度/比例/抽卡/输出格式 + 价格预估）、**视频**（异步任务接口）。

与本仓库其他组件的关系：`dsh-plugins/dsh-image-edit/` 是 DSH 挂件原型；`compose/images/mask_edit_app.py` 是工具站服务本体；本目录是 **ZCode MCP 插件**形态——ZCode 没有侧栏按钮，插件负责把本地画布拉起来并打开浏览器。

## 本机要求

- Python 3.10+，已装 Pillow（`pip install -r requirements.txt`）
- 中转站提供 `POST {base}/images/edits`（multipart）和可选的 `GET {base}/models`

## 直接打开画布（不经过 ZCode）

```bash
python3 server/mask_edit_app.py --port 8000
```

浏览器打开 http://127.0.0.1:8000/

只监听本机，没有鉴权，不要暴露到公网。

## 接口配在哪

插件包里没有密钥。本机默认读（凭据只走环境变量与本机文件，不进仓库）：

`~/.zcode/image-edit.local.json`（Windows 即 `%USERPROFILE%\.zcode\image-edit.local.json`）

```json
{
  "base_url": "https://your-relay.example.com/v1",
  "api_key": "sk-...",
  "model": "gpt-image-2"
}
```

画布打开时会预填这三项。页面里改过会记在浏览器 localStorage，优先于文件；也可以设环境变量 `IMAGE_EDIT_BASE_URL` / `IMAGE_EDIT_API_KEY`。页面上点「保存为本机默认」可把浏览器里的配置写回该文件（带自定义头校验，防恶意网页跨域覆盖）。

## 主要功能

**改图栏**

- 涂抹遮罩：画笔 / 矩形对象（可选中拖动、Delete 删除、提交时固化）/ 橡皮 / 反选 / 全填 / 复制遮罩
- 作用域：仅遮罩区（涂红重画，不发干净原图）或整图重画
- 结果查看器：缩略图画廊 + 全屏模式（单张缩放平移、**按住对比**——按住看原图松开看改后、并排对比、滑动对比），多张抽卡结果左右切换
- 拖拽 / Ctrl+V 粘贴外部图片（QQ/微信聊天图），跨域拉不下来时自动走本机服务代理

**生图栏**

- 清晰度 1K/2K/4K × 宽高比（自动合成 size）× 抽卡数量 1–4 × 输出格式 png/jpeg/webp
- 价格预估（价目表为前端常量，可按自己中转站的计费改）
- 引擎：GPT（gpt-image-2 / 2.5 flare / 2.5 sunburst）与 Grok 文生图

**视频栏**

- `POST /videos` 异步任务（提交 → 轮询 → 下载），上游 404 时自动回退同步 `/videos/generations`；完成后页面内播放/下载

**通用**

- Base URL 不写 `/v1` 自动补全；上游错误完整记入 server 日志便于排障
- `502 Upstream access forbidden` 视为瞬时上游故障，直接重试

## 页面里还可以改

1. Base URL，到 `/v1` 为止
2. API Key（只存在本机配置或浏览器 localStorage）
3. 模型名（可用「测试」「获取模型列表」）
4. 选图 → 涂抹/框选要改的区域 → 提示词 → 提交

作用域选「仅遮罩区」时：只发涂红图，不发干净原图（否则模型会把那块「恢复」）。

## 作为 ZCode 插件

源码在本目录。安装后对新任务说「打开改图」，或用命令 `/image-edit`。模型应调用 `image_edit_open`，而不是替你猜遮罩。
