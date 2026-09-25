# WSL 通道（方案 A）· 用法、边界与纪律

一句话：**Windows 仍是唯一主环境**；本目录只提供"把无状态脚本交给 WSL 跑"的入口与机械门禁。
不改任何既有 `.py`，不搬 DSH，不搬出图流水线。

## 1. 组成

| 文件 | 作用 |
|---|---|
| `wslrun.sh` | **唯一入口**。对齐 `HOME` 到 Windows 家目录、注入凭据、激活 venv、`exec` 目标脚本；启动时把解析结果回显到 stderr |
| `doctor.sh` | 机械门禁 G2–G6；`--io <目录> [--repeat N]` 追加 I/O 计时。任一 FAIL → 退出码 1 |
| `probe_env.py` | 环境探针（走真实代码路径 `mask_edit_app.env_cred()`）。**只回显布尔与路径，绝不回显凭据值** |
| `bootstrap.sh` | 一次性引导：建 venv 并装固定版本依赖（幂等） |
| `requirements.txt` | WSL 侧依赖，版本刻意对齐 Windows 侧 `C:\Python314` |

仓库外（不提交）：`~/.venvs/mantu/`、`~/.config/mantu/relay.env`（权限 600，三个键）。

## 2. 固定调用式

```powershell
# Windows 侧：全 ASCII、只有路径 —— 这正是本通道存在的意义
$env:WSL_UTF8='1'
wsl.exe -d Ubuntu-24.04 -e bash /mnt/c/Users/typ/Desktop/mantu/tools/wsl/doctor.sh
wsl.exe -d Ubuntu-24.04 -e bash /mnt/c/Users/typ/Desktop/mantu/tools/wsl/wslrun.sh <脚本绝对路径> [参数…]
wsl.exe -d Ubuntu-24.04 -e bash /mnt/c/Users/typ/Desktop/mantu/tools/wsl/wslrun.sh -- jq . < /mnt/c/...   # 管道/文本工具逃生口
```

**不提供 `-c <内联代码>` 入口**：内联命令正是要消灭的那类故障（见 §5 的第 3 条实测）。

## 3. 结果怎么读（踩过，别重复）

**不要让 pwsh 管道捕获 `wsl.exe` 的 stdout**——实测会拿到 0 行/乱码（wsl.exe 自身消息与发行版输出混流，编码也不定）。
可靠做法：**在 bash 侧重定向到文件，再用 read 工具读**：

```powershell
wsl.exe -d Ubuntu-24.04 -e bash -c 'bash /mnt/c/Users/typ/Desktop/mantu/tools/wsl/wslrun.sh <脚本> <参数> > /mnt/c/Users/typ/AppData/Local/Temp/out.txt 2>&1'
```

## 4. 白名单 / 黑名单

**适合（无状态、只吃命令行给的路径）**：`tone_report.py`、`fetch_url.py`、`erase_region.py`、`local_ops.py`、skill 的 `scripts/*.py`，以及 jq/sed/awk/grep 类文本管道。

**禁止**：
1. 出图链路（`run_round.py` / `gen*.py` / `mask_edit_app.py`）——**除非 G3 通过**，且注意跨文件系统折损；
2. `dsh-plugins/*`、任何读写 `~/.dsh` / `~/.agents` / `~/.zcode` 状态的脚本、`acceptance.py`（其 A4/B 段依赖 `Path.home()` 与 `sys.executable`，**只在 Windows 跑**）；
3. 需要走 Windows 本地代理（`127.0.0.1:7890`）的下载——该代理在 WSL 不可达，要在 Windows 侧做；
4. **`node.exe`**：WSL 里 `npm`/`npx`/`pnpm` 是 Windows 侧 shim 漏进来的（`node` 本身不存在），而 `node.exe` 又能被 interop 拉起——两者都会变成"在 Linux 里跑 Windows 进程"的混语义。

## 5. 三个已实测的坑（都已加防御）

1. **`. 文件` 只设 shell 变量，不导出给子进程** → 症状是 `[ -n "$RELAY_API_KEY" ]` 为真、Python 里却是空的。`wslrun.sh` 已显式 `export` 三个键。
2. **凭据文件 CRLF** → bash 源码化报 `$'\r': command not found`，叠加 `set -e` 直接整脚本 127 退出。`wslrun.sh` 用进程替换 + `tr -d '\r'` 读凭据，已对此免疫。
3. **`/mnt/c`（9p）读比 Windows 原生慢约 2×**（实测 30 张/47 MB：0.637s vs 0.326s），而 Linux 原生副本是 0.348s（≈1.07×）。先 `cp` 到 Linux 侧再跑合计≈0.61s，**等于没有收益** → 结论：**图片批处理不进 WSL**，通道用于文本/管道与 Linux 工具链场景。

## 6. 门禁

```powershell
wsl.exe -d Ubuntu-24.04 -e bash /mnt/c/Users/typ/Desktop/mantu/tools/wsl/doctor.sh --io <产物目录> --repeat 3
```

判据与不通过时的处置见 `docs/环境_Windows与WSL2混用.md`。**改完本目录任何 `.sh` 都要重跑 doctor**：`.gitattributes` 是 `* -text`（字节原样），git **不会**替我们把 CRLF 转成 LF。

## 7. 行尾约定（有意与仓库其余文件不同）

本目录**全部文件**（含 `.md`/`.py`/`.txt`）一律 **LF**，而仓库其余文件统一 CRLF：

- 技术必需：`.sh` 若带 CRLF，bash 会报 `$'\r': command not found`；
- 既然必需 LF，目录内就保持一致，避免"同一个目录里两种行尾"这种更难查的状态；
- `* -text` 下 git 按字节原样存储，**不会**互相改写。
