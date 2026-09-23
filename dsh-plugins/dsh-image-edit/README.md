# dsh-image-edit · DSH Web「改图 / 图片」挂件

给 [DSH](https://www.npmjs.com/package/@deepseek-ai/dsh) 的 Web GUI 加两个侧栏按钮：

- **改图** —— 打开一个本地「遮罩改图」页：在图上涂抹要改的区域，填 Base URL / API Key / 模型，调用
  OpenAI 兼容的 `POST /images/edits`（图生图）出结果。
- **图片** —— 打开一个本地「图片画廊」：按分类看当前一轮的图，页内灯箱预览（点空白关闭、
  滚轮缩放、放大后可拖动平移、`←/→` 翻图）。

两个按钮都是**点一下才启动服务**：不需要事先开着一个终端窗口。服务起不来时，按钮上会直接显示原因（悬停看 title）。

> 作者环境：Windows + DSH `0.1.2-rc.1` + Node v24 + Python 3.14（Pillow / numpy）。
> 本插件是"客户端半边 + 节点半边 + 一个本地 Python 服务"三块拼起来的，下文把每块的契约与踩过的坑都写清楚了。

---

## 1. 架构：三块，各管一段

```
┌─ 浏览器（DSH Web GUI, 同源 http://127.0.0.1:3080）
│   ├─ 侧栏底部两个按钮 ......... lib/client.js   （客户端半边：只注册 UI，不做文件/进程操作）
│   └─ fetch 同源路由
│        POST /dsh-image-edit/ensure   ← 探活；没起就拉起并等它响应
│        GET  /dsh-image-edit/status   ← { running, url, label, pid }
│        POST /dsh-image-edit/stop     ← 停掉"本插件启动的那个" pid
│              ↑ 由 lib/index.js（节点半边）注册在 DSH 的 WebServer 上
│                    └─ 需要时 spawn 本地 Python 服务（detached、独立进程组、stdio ignore）
└─ 本地服务 mask_edit_app.py ──► http://127.0.0.1:8000
     ├─ GET  /             遮罩改图页
     ├─ POST /api/ping     连通性 + 可用模型数
     ├─ POST /api/models   拉模型列表
     ├─ POST /api/edit     调中转站 /images/edits
     ├─ GET  /gallery      图片画廊（分类页签）
     └─ GET  /gallery/img  图片字节（仅白名单根目录内的图片后缀）
```

### 为什么这样切分

| 决策 | 原因 |
|---|---|
| **懒启动**而不是要求用户先手动开服务 | 常态并不需要这个服务；只在点按钮那一下起最省事。pid 落盘 `.dsh-image-edit.pid`，所以 DSH 重启后 `/stop` 仍然管用 |
| 节点半边用 `spawn(detached)` 而**不是** `ctx.subprocess` | subprocess 这个 seam 会在服务销毁时**连带杀掉**它管理的所有进程，而本地服务应当比 DSH 活得更久 |
| 客户端半边**只依赖 `slots`**，其余一概不做 | `inject` 里 await 一个不存在的服务会让条目永远 pending；而且 `apply` 一旦抛异常会**让整个 web-shell 启动失败** |
| 探活用 `node:http` 而**不是** `fetch` | 本机实测（Node v24.18.0）：对一个以 HTTP/1.0 应答的服务 abort 一个 fetch，会在 undici 内部抛**不可捕获**的断言（`AssertionError: assert(!this.paused)`），它来自 socket 事件处理器 → 会**杀掉整个 DSH 宿主进程**（= 整个 GUI 挂掉）。`node:http` 的 `req.destroy()` 是文档化的取消方式，没有这条路径 |
| 路由挂在 `/api` **之外** | `/api` 前缀被 `dsh-client-connection` 的浏览器信任栅栏独占；插件自己的路由放在别的前缀才能被同源页面直接 fetch |

---

## 2. 安装

### 前置
- **Python 3.10+**（作者用 3.14），需要 `Pillow`、`numpy`；改图页用到 `cv2` 的功能可选装。
- Node 侧无额外依赖（客户端半边只用 `react` / `react/jsx-runtime`，由宿主提供）。

### 三步装好

```bash
# 1) 把本目录挂进 profile（用 link: 指向本目录绝对路径）
dsh plugin --profile web add link:/abs/path/to/dsh-image-edit

# 或者不污染 profile，临时试：
dsh --profile web --patch ./dev.patch.yml
```

2) **改掉 `cordis.patch.yml` 里的本机路径**——下面这些默认值是作者机器上的，必须换成你自己的：

```yaml
config:
  url: 'http://127.0.0.1:8000'      # 本地服务监听地址 = 按钮打开的地址
  label: '改图'                      # 按钮文字
  routePath: '/dsh-image-edit'       # 本插件路由前缀（故意放在 /api 之外）
  port: 8000
  python: 'C:\Python314\python.exe'                                   # ← 改成你的解释器
  serverScript: 'C:\Users\typ\Desktop\mantu\compose\images\mask_edit_app.py'  # ← 改成你的路径
  serverCwd: 'C:\Users\typ\Desktop\mantu\compose\images'               # ← 同上
  logFile: 'server.log'
  startTimeoutMs: 25000              # /ensure 等它起来的上限
```

3) **重启 `dsh web`**，然后刷新页面。节点半边只在启动时加载一次；客户端半边改动只需刷新页面。

（`package.json` 里 `dsh.client.inject` 声明了用到的两个客户端包；`engines.dsh` 声明最低版本。）

---

## 3. 契约：写这类挂件必须知道的事

### 客户端半边（`lib/client.js`）

- 文件必须是**loader 包装的惰性 CJS**：`window.__ModuleLoader__.load({ id, factory })`，
  脚本本身**只注册工厂**，真正的体在首次 import 时执行。
- 槽位 `sidebar.footer.action` 的 owner props **只有 `{ wide: boolean }`**
  （宿主是 `renderSlot("sidebar.footer.action", { wide })`）。所以 url 与 label 不能靠 props 传，
  本插件的做法是**从路由的应答里回读**。
- 一个槽里放多个条目 → **`id` 必须互不相同**（本插件：`image-edit` 与 `image-gallery`）。
- `ctx.slots.inject(name, cb)` 在槽出现时执行一次 `cb`；`ctx.slots.register({ name, id }, Component)`
  返回 disposer。
- `apply` **绝不能抛**：抛了会 fail 整个 web-shell 启动。所有入口都包 try/catch 并降级。

### 节点半边（`lib/index.js`）

- **改它必须重启 `dsh web`**（node 半边只在 boot 时加载）。
  注意 `profile.dsh.patchReload: "live"` 只覆盖**patch 文件**，不覆盖 node 半边的 JS。
- 注册路由：`ctx.webServer.register({ kind: 'exact', path, handler })`，
  并用 `ctx.effect(() => registerRoutes(...), name)` 包起来（与官方 `dsh-webhook-github` 一致）。
- 读配置要**逐键夹取默认值**：`readConfig()` 把每个键都 clamp 到默认，绝不假设 config 形状。

### 本地服务（`mask_edit_app.py`）

- 标准库 `ThreadingHTTPServer`，无框架依赖。
- **模块级用到的模块必须在模块级 import**。实测教训：`os` 只在函数内部 import，
  而模块级写了 `os.path.join(...)` → 启动即 `NameError`，表现为"按钮点了只报 503"。
- 服务是**独立进程**，改它只需重启它自己：
  ```bash
  curl -X POST http://127.0.0.1:3080/dsh-image-edit/stop
  curl -X POST http://127.0.0.1:3080/dsh-image-edit/ensure
  ```
  这样不会影响 GUI（不用重启 `dsh web`）。

---

## 4. 前端踩过的坑（画廊 / 灯箱）

这几条都是实测踩出来的，做同类预览器可直接抄结论：

1. **flex 居中 + 内容溢出 = 滚动范围被吃掉**
   `.lb-stage` 原来用 `display:flex; align-items:center; justify-content:center`。
   当子元素**比容器大**时，居中会把溢出部分推到滚动起点之外 → **放大后拖不到最上/最左**。
   ✅ 正解：容器只 `display:flex`，**居中式样交给子元素 `margin:auto`**
   （小的时候自动居中，大的时候归零，滚动范围完整）。
2. **滚轮缩放要拦默认滚动**：`addEventListener('wheel', h, { passive:false })` + `preventDefault()`；
   否则滚轮在缩放的同时把页面也滚了。
3. **缩放基准要选"适应窗口尺寸"，不是原图像素**。以原图像素为基准时，第一格
   `zf: 1 → 1.06` 会把宽度从"适应窗口宽"直接跳到"1.06 × 原图宽"——大图下第一下就能跳到 1.5 倍，
   表现为"第一下特别快，后面每格却只有 6%"。
   ✅ 正解：图片 `onload` 后量一次适应窗口的实际尺寸 `fitW`，`width = fitW × zf`；
   倍率按原图像素显示（100% = 1:1），并把点击行为定为"适应窗口 ↔ 真正 1:1"。
4. **滚轮步进要按位移算，并归一化 `deltaMode`**：
   `factor = exp(-Δy × k)`（本插件 k=0.0006，一格 ≈ ×1.06），
   `deltaMode===1` 时 Δy ×16、`===2` 时 ×100——否则换设备（鼠标 / 触控板）步长会差几十倍。
5. **点击空白关闭要覆盖"舞台"**：图周围那片空白命中的是 `.lb-stage`，不是最外层容器；
   只判 `e.target === lb` 会关不掉。
6. **拖动平移用 Pointer Events + `setPointerCapture`**（拖出元素范围不断线），
   并且位移超过阈值（本插件 3px）要**抑制随后的 click**，否则拖完会误触发"切换缩放"。
   触屏还要 `touch-action:none`，否则拖动被页面滚动抢走。

---

## 5. 测试（都能离线跑，不需要浏览器）

| 命令 | 覆盖 |
|---|---|
| `node _test_client_button.mjs` | 客户端半边：在 vm 里跑 `lib/client.js`，假 React / 假 fetch / 假 `window.open`；断言"先 ensure 再开页""路由缺失时回退默认地址""服务起不来时不打开注定失败的页面"，以及两个按钮 id 不冲突 |
| `node _test_lazy_start.mjs` | 节点半边 **真跑**（会真的拉起本地服务，需先配好 Python 路径）：注册了 3 条路由 → `status` 报未运行 → `ensure` 把它拉起来并回传 pid → **服务真的能应答** → 再 `ensure` **不会重复启动**（pid 不变）→ `stop` 停掉 |
| `python mask_edit_app.py --port 8011` | 服务自检：能起来就说明**模块级**没有问题（上面那个 `NameError` 就是靠它暴露的） |
| `python style-distill/assert_gallery_categories.py` | （本项目内）画廊分类回归断言 64 条 |

---

## 6. 已知限制

- **节点半边改动需要重启 `dsh web`**；只有客户端半边能靠刷新页面生效。
- 画廊的"用户输入图"索引依赖**本项目**的会话日志与目录约定（`style-distill/round_*/`），
  不属于通用功能；直接搬走时请把 `scan_roots()` / `user_inputs()` 换成你自己的来源。
- 改图页假设接口是 **OpenAI 兼容的 `/images/edits`**（`base_url` + `api_key` + `model`）；
  不同中转站的字段与体积上限需要自己实测（本项目实测：表单上限约 1.96 MiB，
  改用 **JPEG 投喂**可比 PNG 小约 5 倍）。
- 只监听 `127.0.0.1`，**没有鉴权与多用户设计**，不要直接暴露到公网。

---

## 7. 发布前检查清单（**开源前必读**）

- [ ] **清掉硬编码密钥**：`mask_edit_app.py` 第 **73 / 91 / 618 / 784 / 794 / 1172** 行各有一把 `sk-…`；
      其中第 618 行是 HTML 里 `<input value="sk-…">`，**会随页面发给任何访问者**。
      改成读环境变量或本地未跟踪的配置文件。
- [ ] **重置已泄露的 key**：它们已经进了 git 历史、会话记录与本机日志——开源前请到中转站后台重新生成。
- [ ] 清掉本机绝对路径（`C:\Users\typ\...`、`C:\Python314\...`）。
- [ ] `package.json` 目前是 `"private": true`；要发布 npm 包则改为 `false` 并补 `repository` / `license` / `files`。
- [ ] **选许可证并加 `LICENSE`**（本仓库尚未声明；建议 MIT，由发布者决定）。
- [ ] 不要把个人素材一起发出去（本项目仓库里含大量参考图与生成结果）。

---

## 8. 文件清单

```
dsh-image-edit/
├─ package.json          # 包声明：main=节点半边、./client=客户端半边、dsh.client/bundle 声明、engines
├─ cordis.patch.yml      # 挂载行与全部配置项（装机时改这里）
└─ lib/
   ├─ index.js           # 节点半边：读配置、注册 3 条路由、懒启动本地服务、pid 落盘
   └─ client.js          # 客户端半边：往 sidebar.footer.action 注册两个按钮

../_test_client_button.mjs   # 客户端半边离线测试
../_test_lazy_start.mjs      # 节点半边离线测试
```
