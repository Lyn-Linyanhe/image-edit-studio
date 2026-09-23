# 改图插件 · dsh-image-edit（DSH Web 挂件）

> **用途：私下交流用**——给同行看这个「改图」挂件是怎么做的、实测到什么、踩过哪些坑。
> 不是对外发布物（无 LICENSE、未发布 npm）。

给 [DSH](https://www.npmjs.com/package/@deepseek-ai/dsh) 的 Web GUI 加一个侧栏按钮 **「改图」**：
点开是一个本地网页，**在图上涂抹要改的区域** → 填 Base URL / API Key / 模型 + 提示词 → 调中转站的
图生图接口出结果。按钮**点一下才启动本地服务**，不用事先开终端；服务起不来时按钮上直接显示原因（悬停看）。

**为什么要有它**：聊天客户端和中转站自己的控制台都**不给你画遮罩的地方**——而这套接口的"局部改图"
恰恰要靠遮罩。于是做一个本地小服务：给你一块真正的涂抹画布，由它来拼请求。

作者环境：Windows + DSH `0.1.2-rc.1` + Node v24 + Python 3.14（Pillow / numpy；无 Docker、无 GPU）。

---

## 1. 它长什么样（界面上的东西）

| 区域 | 控件 | 作用 |
|---|---|---|
| 图片 | 选文件 / 追加多张 / 复制遮罩 / 清空列表 | 内容图可以多张（按引擎能力决定能不能一起发） |
| 画布 | 画笔 / 橡皮 / 清空 / **反选** / 适应窗口 | 涂抹区 = 要改的区域；反选 = 涂哪保哪 |
| 参考图 | 添加参考图 / 清空参考图 | 身份、画法、姿态参考，按角色挂上去 |
| 引擎 | 引擎选择 / 作用域（整图 · 仅遮罩区） | 决定走哪个上游、以及是整图重画还是只改遮罩区 |
| 接口 | Base URL / API Key（可切换明文）/ 测试 / 获取模型列表 | 连通性与可用模型 |
| 参数 | 模型 / 提示词 / 质量 / 分辨率 | 提交给上游的生成参数 |

---

## 2. 一次"改图"的请求链路

```
浏览器改图页
  │  multipart POST /api/edit   （本地服务，127.0.0.1:8000）
  │  字段：base_url, api_key, model, prompt, size, quality,
  │        pad_mode, mask_mode, scope, engine, resolution, operation
  │  文件：内容图 + 遮罩 + 若干"带角色标签"的参考图
  ▼
本地服务 mask_edit_app.py
  │  ① 把**要改的区域硬涂成纯红**，合成进 image[1]  （关键，见第 3 节）
  │  ② 组装上游请求：image / image[1] / image[2…] (+ mask alpha)
  ▼
中转站 OpenAI 兼容接口  POST {base_url}/images/edits
  ▼
结果回传页面（b64 或 url），可下载
```

## 3. 遮蔽是怎么做到的（这是这个插件的核心发现）

- **`/images/edits` 是 multipart，但它的 `mask` 字段会被静默忽略**——发过去没有任何效果。
- 真正被认的是：**把"要改的区域"硬涂成纯红，作为 `image[1]` 一起发**，
  再在提示词里明确"红色只是标记、只有这一块要改、其余保持原样"。
  实测**保护区 100% 不动**（在项目里进一步量到"保护区最大改动 0.0"）。
- 代价：硬涂红会把该区域的原有信息整块抹掉，模型只能靠提示词重建——
  所以它适合"**这块本来就要清掉重画**"（换背景、重画某件道具），不适合"保留结构、整体加色"。
- 一个反直觉的补充（本项目另一处实测）：**把干净原图一起发过去时，模型会照抄它把那块"恢复"**，
  于是正向改图可能变成"近原图返回"。**只发涂红那张（不发干净原图）才会真的重画**——
  插件页里的"作用域 / 遮罩模式"就是在切这两种用法。

---

## 4. 实测账本（来自代码头部的实测注释，逐条都对得上）

### gpt（`gpt-image-2`）
- 无 `mask` 字段，遮蔽靠 `image[1]` 红标 + 明确指示（保护区实测 100% 不动）。
- 结果以 **b64_json** 返回。
- **支持多图**：`image + image[1] + image[2]` 三张实测可用。
- **尺寸不严格**：请求 `1024x1536` 实际回到过 `1029x1528`；请求 `1024x1024` 回到过 `1254x1254`。
  → 任何"跟随原图比例"的功能只能承诺近似比例，**不要在其上做像素级精确假设**。
- 账号只暴露**一个**模型（`gpt-image-2`），所以"获取模型列表"只显示一条是正常的，不是 bug。
- `HTTP 502 {"Upstream access forbidden…"}` 是**瞬时上游故障**（不是坏请求，坏请求是 400）：
  **重试即可**，别急着查代码。

### grok（`grok-imagine` / `grok-imagine-edit`）
- 文生图**只有带 `response_format="b64_json"` 才可用**：默认回的是 `imgen.x.ai` 上的 url，
  而本网络解析到 `162.125.1.8` 后连接超时 → 图永远下不回来。
- **图生图不可用**：`/images/edits` 会忽略 `response_format`，于是永远回那个不可达的 url。
- `grok-imagine-edit` **不接受超过一张参考图**（HTTP 400）。
- 它按规范**不要发 OpenAI 的 `quality`**，改用 `resolution`（1k/2k）驱动输出尺寸。

### 体积（本项目实测，跨接口通用）
- 表单上限约 **1.96 MiB 通过 / 2.12 MiB 起被拒**（`400 form field too large or incomplete`）。
- 投喂体积由**目标尺寸**决定，与源图分辨率无关（把参考缩到 320px，归一化到 4K 后仍要 1.51 MiB）。
- **改用 JPEG 投喂可比 PNG 小约 5 倍**：同一尺寸同一对图，PNG 2.80 MiB → JPEG q88 0.56 MiB
  （PNG 无损、且投喂前会先放大到目标尺寸，量化/降采样那套省字节的办法基本无效）。

---

## 5. 安装

### 前置
- **Python 3.10+**（作者用 3.14）：`Pillow`、`numpy`；部分功能用 `cv2`（可选）。
- Node 侧无额外依赖：客户端半边只用宿主提供的 `react` / `react/jsx-runtime`。

### 三步
```bash
# 1) 把本目录挂进 profile（link: 指向本目录绝对路径）
dsh plugin --profile web add link:/abs/path/to/dsh-image-edit
# 或者不污染 profile，临时试：
dsh --profile web --patch ./dev.patch.yml
```

2) **改掉 `cordis.patch.yml` 里的本机路径**（这三项默认值是作者机器上的）：

```yaml
config:
  url: 'http://127.0.0.1:8000'      # 本地服务地址 = 按钮打开的地址
  label: '改图'                      # 按钮文字
  routePath: '/dsh-image-edit'       # 本插件路由前缀（故意放在 /api 之外）
  port: 8000
  python: 'C:\Python314\python.exe'                                   # ← 换成你的解释器
  serverScript: 'C:\Users\typ\Desktop\mantu\compose\images\mask_edit_app.py'  # ← 换成你的路径
  serverCwd: 'C:\Users\typ\Desktop\mantu\compose\images'               # ← 同上
  logFile: 'server.log'
  startTimeoutMs: 25000              # /ensure 等它起来的上限
```

3) **重启 `dsh web`**，然后刷新页面。
   节点半边只在启动时加载一次；只有客户端半边能靠刷新页面生效。

> 改图页里的 **Base URL / API Key 都是运行时手填**的（可记住在浏览器里），
> 插件包与配置文件里**不含任何密钥**。

---

## 6. 契约：写这类挂件必须知道的事

### 客户端半边（`lib/client.js`）
- 必须是 **loader 包装的惰性 CJS**：`window.__ModuleLoader__.load({ id, factory })`，
  脚本只注册工厂，体在首次 import 时执行。
- 槽位 `sidebar.footer.action` 的 owner props **只有 `{ wide: boolean }`**；
  所以 url / label 不能靠 props 传，本插件从路由应答里回读。
- 一个槽里放多个条目 → **`id` 必须互不相同**。
- `ctx.slots.inject(name, cb)` 在槽出现时执行一次；`ctx.slots.register({ name, id }, Component)` 返回 disposer。
- `apply` **绝不能抛**：抛了会让整个 web-shell 启动失败。所有入口包 try/catch 并降级。

### 节点半边（`lib/index.js`）
- **改它必须重启 `dsh web`**。注意 `patchReload: "live"` 只管 patch 文件，不管 node 半边的 JS。
- 注册路由：`ctx.webServer.register({ kind: 'exact', path, handler })`，
  用 `ctx.effect(() => registerRoutes(...), name)` 包起来（与官方 `dsh-webhook-github` 一致）。
- 三条路由：`POST /ensure`（探活，没起就拉起并等它响应）、`GET /status`、`POST /stop`。
- 读配置要**逐键 clamp 到默认值**，绝不假设 config 形状。
- 用 `spawn(detached, stdio:'ignore')` 而不是 `ctx.subprocess`：后者的 seam 会在服务销毁时
  **连带杀掉**子进程，而本地服务应当比 DSH 活得更久。pid 落盘 `.dsh-image-edit.pid`，重启 DSH 后 `/stop` 仍管用。
- 探活**只用 `node:http`，不要用 `fetch`**：本机实测（Node v24.18.0）对一个以 HTTP/1.0 应答的服务
  abort 一个 fetch，会在 undici 内部抛**不可捕获**的断言（来自 socket 事件处理器）→ **杀掉整个 DSH 宿主进程**。
- 路由挂在 `/api` 之外：`/api` 前缀被 `dsh-client-connection` 的浏览器信任栅栏独占。

### 本地服务（`mask_edit_app.py`）
- 标准库 `ThreadingHTTPServer`，无框架。
- **模块级用到的模块必须在模块级 import**。实测教训：`os` 只在函数内 import 而模块级写了
  `os.path.join(...)` → 启动即 `NameError`，表现为"按钮点了只报 503"。
- 它是**独立进程**，改它只需重启它自己（不影响 GUI）：
  ```bash
  curl -X POST http://127.0.0.1:3080/dsh-image-edit/stop
  curl -X POST http://127.0.0.1:3080/dsh-image-edit/ensure
  ```

---

## 7. 测试（离线可跑）

| 命令 | 覆盖 |
|---|---|
| `node _test_client_button.mjs` | 客户端半边：vm 里跑 `client.js`，假 React / 假 fetch / 假 `window.open`；断言"先 ensure 再开页""路由缺失时回退默认地址""服务起不来时不打开注定失败的页面" |
| `node _test_lazy_start.mjs` | 节点半边**真跑**（会真的拉起服务）：3 条路由 → `status` 报未运行 → `ensure` 拉起并回传 pid → 服务真的能应答 → 再 `ensure` 不重复启动（pid 不变）→ `stop` 停掉 |
| `python mask_edit_app.py --port 8011` | 服务自检：能起来就说明模块级没问题（上面那个 `NameError` 就是靠它暴露的） |

---

## 8. 已知限制

- **节点半边改动需要重启 `dsh web`**；只有客户端半边能靠刷新生效。
- 接口假设是 **OpenAI 兼容的 `/images/edits`**（`base_url` + `api_key` + `model`）；
  不同中转站的字段与体积上限要自己实测（上面第 4 节给了本机的实测数字）。
- **尺寸不严格**（见第 4 节），别在其上做像素级精确假设。
- 只监听 `127.0.0.1`，**没有鉴权与多用户设计**，不要直接暴露到公网。

---

## 9. 转给别人时注意两点

1. **凭证**：本包（`lib/`、`cordis.patch.yml`、`package.json`）**不含任何密钥**（密钥是运行时手填的）。
   配套的本地服务 `mask_edit_app.py` 不属于本包、且带有本机配置，**不要连同它一起转**。
2. **本机路径**：`cordis.patch.yml` 的 `python` / `serverScript` / `serverCwd` 是作者的绝对路径，
   对方要按第 5 节改成自己的。

---

## 10. 附：本项目另外加的「图片」按钮（非通用）

本项目在同一个插件里多注册了一个按钮 **「图片」**，打开本地服务的 `/gallery`：
按分类页签看当前一轮的图，页内灯箱预览（点空白关闭、滚轮缩放、放大后拖动平移、`←/→` 翻图）。

**它绑死了本项目的目录与会话约定，不是通用功能**——直接搬走时必须替换
`scan_roots()` / `user_inputs()` 两个数据来源。若你也做类似的预览器，这几条实测结论可直接抄：

1. **flex 居中 + 内容溢出 = 滚动范围被吃掉**：容器用 `align-items/justify-content:center` 时，
   子元素一旦比容器大，溢出部分会被推到滚动起点之外 → 放大后**拖不到最上/最左**。
   ✅ 正解：容器只 `display:flex`，居中式样交给子元素 `margin:auto`。
2. **滚轮缩放要拦默认滚动**：`addEventListener('wheel', h, { passive:false })` + `preventDefault()`。
3. **缩放基准要用"适应窗口尺寸"，不是原图像素**：后者会让第一格把宽度从"适应窗口宽"直接跳到
   "1.06 × 原图宽"（大图下第一下就像跳了 1.5 倍），而后面每格只有 6%。
4. **步进按位移算并归一化 `deltaMode`**：`factor = exp(-Δy × k)`（k≈0.0006 → 一格 ≈ ×1.06）；
   `deltaMode===1` 时 Δy×16、`===2` 时 ×100，否则换设备步长差几十倍。
5. **点空白关闭要覆盖"舞台层"**：图周围那片空白命中的是中间容器，不是最外层，只判最外层会关不掉。
6. **拖动平移用 Pointer Events + `setPointerCapture`**，位移超阈值要**抑制随后的 click**（否则拖完误触"切换缩放"）；
   触屏还要 `touch-action:none`。

---

## 11. 文件清单

```
dsh-image-edit/
├─ package.json          # 包声明：main=节点半边、./client=客户端半边、dsh.client/bundle、engines
├─ cordis.patch.yml      # 挂载行与全部配置项（装机时改这里）
└─ lib/
   ├─ index.js           # 节点半边：读配置、注册 3 条路由、懒启动本地服务、pid 落盘
   └─ client.js          # 客户端半边：往 sidebar.footer.action 注册按钮（改图 / 图片）

../_test_client_button.mjs   # 客户端半边离线测试
../_test_lazy_start.mjs      # 节点半边端到端测试
```
