# 环境 · Windows 主环境 + WSL2 薄通道（方案 A）

> 口径标注：**【实测】**本次真的跑出来、【文件核实】读代码/文件得出、【判断】推断、【未验证】证据不足。
> 建立日期 2026-09-25；配套使用说明见 `tools/wsl/README.md`；门禁脚本 `tools/wsl/doctor.sh`。

## 0. 结论

- **采用方案 A**：DSH、插件、出图流水线、技能与凭据**全部留在 Windows**；WSL2 只作为"无状态脚本/文本管道"的执行器。
- **通道已建成并通过门禁**：G2–G6 全 PASS（`doctor.sh` 退出码 0）【实测】。
- **适用边界由实测数字决定，不是由偏好决定**：`/mnt/c` 的 9p 折损有两种量级——**大文件约 2×、海量小文件约 12–20×**（§3.3、§3.4）→
  **图片批处理、以及"数据在仓库"的一次性批处理都不进 WSL**；判据是**数据在哪**，不是"是不是文本"。
- **VS Code 的角色**（§3.5 实测）：**不进 mantu 日常流程**（这条链路的动作全由 agent 执行，它不参与自动化）；
  只有"人要在 Linux 侧编辑/调试"时才值得用，且要先接受 **633 MB 磁盘 + 连接期约 0.9 GB 内存常驻**（关窗口不释放）。
- 不采用方案 B（把 DSH 搬进 WSL）：本机**没有任何"非 Linux 不可"的日常工具**，而 GPU 在 Windows 侧已可用（见 §1）。
- 不采用方案 C（本地生成栈）：与"用不用 WSL"是两件独立的事，本次不做。

## 1. 本机实测清单

### 1.1 已具备

| 项 | 值 | 出处 |
|---|---|---|
| WSL 本体 | 2.7.13.0，内核 6.18.33.2-2，WSLg 1.0.73.2 | 【实测】`wsl --version` |
| 发行版 | **Ubuntu 24.04.4 LTS，VERSION 2**，用户 `typ`/uid 1000 | 【实测】`wsl -l -v` |
| WSL 内 Python | 3.12.3 + `venv`/`ensurepip` 可用 | 【实测】 |
| WSL 内其他 | git 2.43.0、curl 8.5.0、requests | 【实测】 |
| **GPU 直通** | `nvidia-smi` = RTX 5060 Laptop 8151 MiB / 驱动 610.47；`/dev/dxg` 在位 | 【实测】 |
| 网络 | pypi TUNA 直连可用（装包 11–18 MB/s）；`image-direct.geiliapi.com` 直连可达（`/` 返回 404，1–5s） | 【实测】 |
| 文件可见性 | `/mnt/c` 可访问；`~/.dsh`、`~/.agents`、`~/.zcode` 均可在 `/mnt/c/Users/typ/…` 下看到 | 【实测】 |
| 磁盘 | WSL 根盘 953 GB 可用；`/mnt/c` 136 GB 可用 | 【实测】 |
| **Windows 侧 CUDA** | `D:\Anconda3\envs\dl-cv`：torch 2.11.0+cu128、`cuda_available True`、`arch_list` 含 `sm_120`、设备即该 5060 | 【实测】 |

> 关于"要不要为了 GPU 搬 WSL"：**不需要**。Windows 侧 CUDA 已实测可用，WSL 的 GPU 直通只对"必须跑在 Linux 的依赖"有意义。
> 关于"WSL 会不会更快"：不会。同一台机的跨文件系统读反而慢（§3），网络走同一条物理链路。

### 1.2 缺失（本次已补齐或按纪律不补）

| 项 | 状态 |
|---|---|
| PIL/numpy/cv2 | **已装**（venv `~/.venvs/mantu`，版本对齐 Windows：pillow 12.3.0 / numpy 2.5.2 / opencv-headless 5.0.0.93）【实测】 |
| 出图凭据 | **已接**（`~/.config/mantu/relay.env`，600，三键；仓库内无任何密钥）【实测】 |
| `HOME` 差异 | WSL `HOME=/home/typ`，与 `~/.agents`、`~/.dsh` 的真身（`/mnt/c/Users/typ`）**不是同一个家** → 由 `wslrun.sh` 对齐 【实测】 |
| `jq` | 未装（apt 候选 1.7.1）。需要文本管道时再装 |
| `node` | **不装**（DSH 不搬 WSL）；注意 `npm`/`npx`/`pnpm` 是 Windows 侧 shim 漏进 PATH 的假象 【实测】 |
| Windows 本地代理 | 控制面板已启用 `127.0.0.1:7890`；**WSL 不可达**（宿主网关 `172.18.64.1:7890` 亦不可达）→ 需要代理的下载不在 WSL 做 【实测】 |

## 2. 一个被澄清的假故障

建立本通道**之前**同一台机上 `wsl -l -v` 与 `wsl -d Ubuntu-24.04` 双双报
`Wsl/EnumerateDistros/Service/E_ACCESSDENIED`，而 `WslService` 全程 `Running`。
把 DSH 文件策略从 `workspace-write` 改为 `danger-full-access` 后，**同一条命令直接可用**。

因此：【判断】那是 DSH 沙箱拦截，不是 WSL 故障；`WslService` 从未停止过。
→ 后续若再见到该报错，先怀疑**调用者权限/沙箱**，不要先重装 WSL。

## 3. 门禁结果（`doctor.sh`，2026-09-25）

| 门禁 | 判据 | 结果 | 证据 |
|---|---|---|---|
| G2 编码 | 语言环境 UTF-8、中文哨兵不乱码 | **PASS** | `locale charmap=UTF-8`；`WSL_UTF8=1` 下中文往返正常 |
| G3 凭据 | 走真实代码路径 `env_cred('RELAY_API_KEY')` 非空 | **PASS** | `import_ok=true relay_key=true`；对照（刻意不注入）=`false`，说明门禁有区分度 |
| G4 HOME 对齐 | `~/.agents/skills/style-distill/scripts/audit_and_check.py`、`~/.dsh/attachments`、会话目录均存在 | **PASS** | `home=/mnt/c/Users/typ`；三项 `true` |
| G5 I/O | `t_wsl ≤ 1.5 × t_w` 才可承接图片批处理 | **未过（1.95×）** | 见下表 |
| G6 行尾 | 新增 `.sh` 无 `0x0D`、`bash -n` 通过 | **PASS** | 扫过 3 个 `.sh` 全通过 |
| G7 回归 | Windows 侧 `acceptance.py` 31/31 | **PASS** | 提交 `f3509d7` 后实测 **31/31**（C1 扫 697 个文件 0 命中；C5 工作区干净）【实测】 |

### 3.1 G5 三组计时（样本：`t1`，30 张 / 47 MB；各测 3 次取最好）

| 测点 | 最好用时 | 相对 `t_w` |
|---|---|---|
| `t_w` · Windows 侧 `C:\Python314`（NTFS 原生） | **0.326s** | 1.00× |
| `t_wsl` · WSL 读 `/mnt/c`（9p） | **0.637s** | **1.95×** ❌ |
| `t_lin` · WSL 原生 ext4 副本 | **0.348s** | 1.07× |
| 参考：跨文件系统复制同一批（`cp -r /mnt/c/… → ~/`） | **0.257s** | — |

**判读**：折损**全部来自跨文件系统**，WSL 自身只比 Windows 慢约 7%。
"先复制到 Linux 侧再跑"合计 ≈ 0.26 + 0.35 = **0.61s**，与直接读 `/mnt/c` 的 0.637s **同级** → 这个 2× 躲不掉。
→ 按预设判据：**通道收缩为文本/管道任务**；若确需在 WSL 处理图片，必须接受 2× 或明确接受"复制+原生"的等价成本。

### 3.2 两侧等价性（硬证据）

同一批样本在两个环境各跑一次 `audit_and_check.py audit`：

- 输出行数：Windows **71** / WSL **71**【实测】
- 归一化后逐行比对（短哈希 | 尺寸 | 文件名）：**30/30 完全一致**，`Compare-Object` 无差异【实测】

> 方法学备注：第一次比对**假通过**了——归一化函数因正则不匹配返回空集合，`Compare-Object` 收到 `null` 而报"一致"。
> 已改为先断言"归一化行数 > 0"再比对。凡是"比对通过"的结论，都必须同时给出**两侧各自的样本量**。

### 3.3 文本批处理三侧对照（2026-09-25 追加）

同一批文件（HEAD 跟踪的文本文件：283 个 / 2.0 MB / 35300 行）、**同一个脚本**（读全文 + 统计行数 + token 命中），在三处运行：

| 位置 | 最好用时 | 相对 Windows 原生 | 每文件开销 |
|---|---|---|---|
| Windows 原生 python（`C:\Python314`）读 `C:\…` | **0.0545s** | 1.00× | 0.19 ms |
| WSL venv python 读 `/mnt/c/…` | **0.6828s** | **12.5× 慢** | 2.41 ms |
| WSL venv python 读 Linux 侧副本 | **0.0052s** | **10.5× 快** | 0.018 ms |

coreutils 侧同一结论：`wc -l` **0.8099s（/mnt/c）vs 0.0033s（Linux 副本）**；`grep -rl` **0.5437s vs 0.0033s**。
参考成本：把同一批从 `/mnt/c` 复制到 Linux 侧 = **1.0007s**（复制本身也按每文件约 3.5 ms 计费）。
三处结果完全一致（行数 35300、命中 14 个文件）——**这条对照可复现，不是估算**。

**为什么这里（12.5×）比图片批处理（1.95×）大一个量级**：图片是 30 个大文件，代价按**字节**摊（9p 流式读尚可）；
文本是 283 个小文件，代价按**文件打开次数**摊，9p 的每文件开销（~2.4 ms）完全主导。

**外推（非实测）**：文件数越多越致命——1 万个文件时约为 `/mnt/c` ≈ 24s、Windows 原生 ≈ 1.9s、Linux 原生 ≈ 0.18s。
另注：Linux 侧那 0.0052s 受益于页缓存（文件刚解压），冷缓存会慢些，但仍远快于 9p【判断】。

**因此判据改成"看数据在哪"，而不是"看是不是文本"**：

- **一次性 + 数据在仓库** → 留 Windows 原生（最快），别为了用 `grep` 而付 12.5×；
- **要反复迭代同一批数据** → 复制到 Linux 侧（`~/work/…`），此后每轮 0.005s 级，复制成本被摊薄；
- **能力取向**（Windows 侧**根本没有** `grep`/`awk`/`sed`/`wc`/`jq`/`rg`，实测全不在 PATH） → 这时 WSL 的价值是
  **能力，而不是速度**；代价就是上面那个 12.5×；
- `jq` 两侧都缺（WSL 侧 `apt install jq`，候选 1.7.1）。

### 3.4 Windows+WSL2 搭配全项实测（2026-09-25 追加）

电池脚本见 `tools/wsl/bench/`（可复现；跑法与三条方法学纪律见其 README）。同机、同批、同代码。

**A · 环境**

| | Windows | WSL |
|---|---|---|
| OS | Win11 家庭版 build 26100 | Ubuntu 24.04.4，内核 6.18.33.2-microsoft-standard-WSL2 |
| CPU | Intel Core Ultra 9 275HX / 24 逻辑核 | 同一物理 CPU |
| 内存可见 | 32189 MB（整机） | 15703 MB（默认约 50% 上限）；VM 进程 `vmmemWSL` ≈ 1949 MB |
| Python | 3.14.6 | 3.12.3（**版本不同**，故 CPU 项不能直接归因于 OS） |
| 磁盘 | C: 135 GB 可用 | 根盘 952 GB 可用 |

**B · CPU**：同一段纯 Python 整数循环 3e6 次 —— Windows **0.182s**、WSL **0.153s**。⚠️ 解释器 3.14.6 vs 3.12.3，**不可**据此断言 WSL 更快。

**C · 磁盘（3 次取最好）**

| 项目 | Windows 原生 | WSL ext4 | WSL 读 `/mnt/c` |
|---|---|---|---|
| 顺序读 18 MB PNG | 0.020s（≈1280 MB/s） | **0.007s（≈2570 MB/s）** | 0.068s（≈264 MB/s） |
| 顺序写 64 MB | 0.081s | **0.029s** | 0.236s |
| 500 个小文件创建 | **0.295s** | 0.577s | 1.906s |
| 500 个小文件读取 | 0.041s | **0.005s** | 0.802s |

判读：**`/mnt/c` 始终是三档里最慢的**（顺序读慢 3.4×、小文件读慢 20×）；WSL 原生 ext4 在大块顺序 IO 上最快。

**D · 网络**

| 项目 | Windows | WSL |
|---|---|---|
| RTT 均值 `pypi.tuna.tsinghua.edu.cn` | 44.4 ms | 74.5 ms |
| RTT 均值 `image-direct.geiliapi.com` | 397 ms | 412 ms |
| 下载 6.9 MB（**同一绝对 URL**，3 次最好） | 1.807s ≈ 3.8 MB/s | **0.867s ≈ 8.0 MB/s** |
| Windows 本地代理 `127.0.0.1:7890` | 有（WinINET 已启用） | **不可达** |

⚠️「RTT 更低但吞吐更低」（Windows 3.8 vs WSL 8.0 MB/s）是**少量采样**结果，可能与 Windows 侧 TLS/安全软件路径有关【判断】，需复测才能定论；不要据此当结论用。

**E · 双向可达性（NAT 模式，可复现）**

| 方向 | 方式 | 结果 |
|---|---|---|
| Windows → WSL | `http://127.0.0.1:8123/`（localhost 转发） | **200，3.3 ms** |
| Windows → WSL | `http://172.18.74.96:8123/`（WSL 自身的 IP） | **200，2.8 ms** |
| WSL → Windows | `http://172.18.64.1:8124/`（宿主网关 IP；服务绑 `0.0.0.0`） | **200 可达** |
| WSL → Windows | `http://127.0.0.1:8124/` | 不可达（WSL 的 `127.0.0.1` 是它自己） |

⇒ 与 EDA 场景直接相关：**Windows 上的服务（如 hw_server）只要绑 `0.0.0.0` 并放行入站防火墙，WSL 用宿主 IP 即可连上；只绑 loopback 的服务连不上。**

**F · GUI / X（WSLg）**

免安装实测（本机免密 `sudo` 不可用，故不装 `x11-apps`，改用 `gcc` 直接编最小 X11 客户端，见 `bench/xtest.c`）：
`XOpenDisplay=OK (DISPLAY=:0)`、`window_map_state=2`（IsViewable，**窗口真的被合成上屏**）、几何 320x160。
⇒ **WSLg 的 GUI 转发在本机实测可用**，不需要第三方 X 服务器。未验证渲染质量与输入法/键盘。

**G · 边界（编码/行尾/凭据）**

- WSL 写 → Windows 读：**逐字符一致**（`match=True`；字节头 `228,184,173…` 即 UTF-8 的「中」）；
- 凭据仍需显式注入（`RELAY_API_KEY` 在 WSL 环境里默认**不存在**）；
- `.sh` 必须 LF；PowerShell 管道写入会把**末行**变成 CRLF（§4 第 2 条）。

**H · 启动与资源**

| 项目 | 实测 |
|---|---|
| `wsl --shutdown` 后第 1 次调用（冷启动 VM） | **2.89s** |
| 紧接着第 2 次调用（暖） | **0.150s** |
| 暖态 `python3 -V` | 0.160s |
| `tools/wsl/doctor.sh` 全门禁 | 2.17s，退出码 0 |
| VM 内存（`vmmemWSL`） | 运行中 ≈ 1949 MB；`--shutdown` 后**已释放** |

⇒ 冷启动约 3 秒是**每次会话的一次性成本**（"按需拉起"的代价），不是每条命令的成本。

### 3.5 VS Code Remote-WSL 实测（2026-09-25 追加）

**结论：它不是 mantu 流程的组件；只有"人要在 Linux 侧编辑/调试"时才值得用**——但成本必须算清，下面是实测。

| 项 | 实测结果 |
|---|---|
| 安装状态 | VS Code **1.139.0**（`D:\Microsoft VS Code`）；`ms-vscode-remote.remote-wsl 0.104.3` **已装** |
| 连接 | `code --remote wsl+Ubuntu-24.04 /home/typ` —— **连接成功**；WSL 侧起 `server-main.js`（RSS 185 MB）与扩展宿主 `bootstrap-fork`（61 MB），共 12 个相关进程 |
| **server 从哪来** | **由 WSL 内的 `wget`** 拉 `https://update.code.visualstudio.com/commit:<hash>/server-linux-x64/stable`，**不是** Windows 侧下载后送入 → 受 WSL 自身网络影响；实测约 **20 MB/s，不需要代理** |
| **版本变化会重下** | 本次 1.139.0 触发重下，**旧的 server 目录被替换**；`~/.vscode-server` 最终 **633 MB** |
| **内存** | 空闲 WSL **2055 MB** → 连接后 **2935 MB（+880 MB）**；**关掉窗口后 server 不退出**，仍占 **2642 MB**；只有 `wsl --shutdown` 才释放 |
| 远程扩展 | **不是 0 个**：连接后 VS Code 会自动往 WSL 侧装机器级扩展（本次实测自动装了 `ms-ceintl.vscode-language-pack-zh-hans`） |
| 收尾完整性 | 关窗口 + `wsl --shutdown` 之后，`tools/wsl/doctor.sh` 仍退出码 0；仓库状态干净、无残留临时文件 |

**三条纪律**

1. **不要把 VS Code 引入 mantu 日常流程**：这条链路的动作全由 agent 执行，它不参与自动化，只增加入口与"我改的是哪一份"的风险。
2. **要用，就在"数据住在 Linux 侧"时用**（如 `~/work`）——那时 Remote-WSL 是**必需**；若数据仍在 `C:\`，直接在 Windows 侧开即可，不必走远程。
3. **别在有 Remote-WSL 会话时 `wsl --shutdown`**（会切断编辑器）。想收回内存要**先关窗口、再关机**——而"关窗口"本身不够（server 会残留，实测仍占 2.6 GB）。

> 未验证：集成终端里的中文渲染与输入法；`files.eol` 按语言配置能否完全消除假 diff（只做了原理判断，未实跑一次"保存即差分"的对照）。

## 4. 三类实测坑（都已加防御）

1. **`. 文件` 只赋 shell 变量，不导出给子进程**
   症状极隐蔽：脚本里 `[ -n "$RELAY_API_KEY" ]` 为真、而 Python 的 `os.environ` 里是空的（表现为 `relay_key=false` 但同时回显"已注入"）。
   防御：`wslrun.sh` 显式 `export RELAY_API_KEY RELAY_API_KEY_HD RELAY_BASE_URL`。

2. **凭据文件带 CRLF**
   PowerShell 管道给**末行**加了 CRLF（中间行是 LF，字节级已核对）。bash 源码化即报 `$'\r': command not found`，
   叠加 `set -e` 会**让整个入口脚本以 127 退出**（当时表现为探针"无输出"、G3/G4 全空）。
   防御：`wslrun.sh` 用进程替换 + `tr -d '\r'` 读凭据；写入端也用 `tr -d "\r"`。

3. **pwsh 管道捕获 `wsl.exe` 的 stdout 不可靠**
   实测同一命令直接跑有 71 行，经 `2>$null | Out-File` 捕获得到 **0 行**。
   防御：**在 bash 侧重定向到文件**，再用 read 工具读（见 `tools/wsl/README.md` §3）。

## 5. 顺带查出的一个既有缺陷（本次**未改**，需另行决定）

`~/.agents/skills/style-distill/scripts/audit_and_check.py`（与仓库镜像 `style-distill/_skill/style-distill/scripts/` 逐哈希一致）
**没有 UTF-8 前置**（`reconfigure(encoding=…)` 缺失，`grep` 为空）【文件核实】。

后果【实测】：它在 Windows 上被重定向/捕获时按 **cp936** 输出——落盘字节为 `CE C4 BC FE CC A8 D5 CB`（"文件台账"的 GBK），
任何按 UTF-8 解码的读取端都会看到乱码；而在 WSL 侧因系统默认 UTF-8 一切正常。

为什么门禁没抓到：`acceptance.py` 的 B8「脚本自带 UTF-8 前置」只扫 `round_lib/*.py`，**不含 skill 的 `scripts/` 目录**。

**要修的话是一次独立决定**：需同时改仓库镜像与已装副本，否则门禁 A4（逐文件哈希一致）会挂。
本次严格遵守"不改既有 `.py`"，故只记录不动手。

## 6. 纪律（违反会破坏本通道的价值）

1. Windows 是唯一主环境；WSL **不得改变仓库产物**，只做分析/批处理。
1.1 批量任务先问**数据在哪**（§3.3）：一次性 + 数据在仓库 → Windows 原生；要反复迭代 → 先复制到 Linux 侧。
   不要把"文本"直接等同于"该进 WSL"——同一批 283 个文件，WSL 读 `/mnt/c` 比 Windows 原生慢 **12.5×**。
2. 两侧禁止同时写同一输出目录；WSL 侧必须显式 `--out` 或加后缀，便于对账。
3. 涉及出图链路、`dsh-plugins/*`、`~/.dsh`/`~/.agents`/`~/.zcode` 状态、注册表凭据的脚本**一律留 Windows**；`acceptance.py` **只在 Windows 跑**。
4. 禁止在 WSL 调 `node.exe`，也不要用漏进来的 `npm`/`npx`/`pnpm`。
5. 需要 Windows 本地代理的下载不在 WSL 做。
6. 新增 `.sh` 必须 LF（`.gitattributes` 是 `* -text`，git 不会帮我们转）；改完重跑 `doctor.sh`。

## 7. 回退方式（通道是纯增量，回退零成本）

```powershell
Remove-Item -Recurse -Force C:\Users\typ\Desktop\mantu\tools\wsl      # 仓库内新增件，无既有代码被改
wsl.exe -d Ubuntu-24.04 -e bash -c 'rm -rf ~/.venvs/mantu ~/.config/mantu ~/io_sample'
```

因**未修改任何既有 `.py`**，回退后 Windows 侧行为与建立通道前完全一致；`git` 侧只需 revert 提交 `f3509d7`。

## 8. 未验证项（如实标注）

- 【未验证】`.wslconfig` 的 `networkingMode=mirrored` 效果，及其与 Windows 侧 `127.0.0.1:3080` GUI 的 localhost 冲突（本方案未用，故不阻塞）。
- 【未验证】`sub.geiliapi.com` 从 WSL 直连耗时（一次采样 17.3s；Windows 侧经代理反而 SSL 失败）→ 若 WSL 侧要调该站，需单独评估超时预算。
- 【未验证】50–200 MB 量级样本的 I/O 比例是否与 47 MB 样本一致（当前只测了一档）。
- 【未验证】方案 B（把 DSH 搬进 WSL）下 harness 自身模型流量能否直连（本地代理在 WSL 不可达，直连能力未测）——本次不做该方案，记录以备将来。
