# 环境 · Windows 主环境 + WSL2 薄通道（方案 A）

> 口径标注：**【实测】**本次真的跑出来、【文件核实】读代码/文件得出、【判断】推断、【未验证】证据不足。
> 建立日期 2026-09-25；配套使用说明见 `tools/wsl/README.md`；门禁脚本 `tools/wsl/doctor.sh`。

## 0. 结论

- **采用方案 A**：DSH、插件、出图流水线、技能与凭据**全部留在 Windows**；WSL2 只作为"无状态脚本/文本管道"的执行器。
- **通道已建成并通过门禁**：G2–G6 全 PASS（`doctor.sh` 退出码 0）【实测】。
- **适用边界由 G5 的数字决定，不是由偏好决定**：`/mnt/c` 的 9p 读取比 Windows 原生**慢约 2×**，超过预设的 1.5× 门槛 → **图片批处理不进 WSL**；通道用于文本/管道与 Linux 工具链。
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
