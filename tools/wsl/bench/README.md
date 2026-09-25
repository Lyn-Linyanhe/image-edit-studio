# bench · Windows+WSL2 搭配实测电池

这一目录是**实测证据的可复现工具**，不是产品路径。结果与判读见 `docs/环境_Windows与WSL2混用.md` §3.4。

## 怎么跑（全 ASCII、只有路径）

```powershell
# ① WSL 侧（先跑，它会写出一个文件给 Windows 侧读，用于编码往返验证）
wsl.exe -d Ubuntu-24.04 -e bash /mnt/c/Users/typ/Desktop/mantu/tools/wsl/bench/bench_wsl.sh
# ② Windows 侧（对称电池；内部会自己调用 cpu_loop.py 与 curl.exe）
pwsh -NoProfile -File C:\Users\typ\Desktop\mantu\tools\wsl\bench\bench_win.ps1
# ③ 下载吞吐（两侧各自跑一次，用**同一个绝对 URL**，否则不可比）
wsl.exe -d Ubuntu-24.04 -e bash /mnt/c/Users/typ/Desktop/mantu/tools/wsl/bench/bench_dl.sh
# ④ 双向可达性（Windows 侧先起一个 0.0.0.0:8124 的服务，再用它从 WSL 侧探）
wsl.exe -d Ubuntu-24.04 -e bash /mnt/c/Users/typ/Desktop/mantu/tools/wsl/bench/probe_host.sh 172.18.64.1
# ⑤ WSLg 窗口验证（免 apt：直接编一个最小 X11 客户端）
wsl.exe -d Ubuntu-24.04 -e bash -c 'T=/mnt/c/Users/typ/AppData/Local/Temp/mantu_g5; gcc -o /tmp/xtest $T/xtest.c -L/usr/lib/x86_64-linux-gnu -l:libX11.so.6 && /tmp/xtest'
```

## 三条方法与纪律（都是踩过才知道的）

1. **两侧必须跑同一份代码、同一批文件、同一个 URL**。第一版对照就是因为两侧语料不同（319 vs 283 文件）而无效，作废重做。
2. **凡是"比对/计时"的结论，都要同时给出两侧样本量**。第一版还犯过"归一化返回空集合 → `Compare-Object` 报一致"的假通过。
3. **不要用 pwsh 管道捕获 `wsl.exe` 或 Windows python 的输出**：实测会拿到 0 行或乱码（wsl.exe 自身消息与发行版输出混流；Windows python 的 stdout 是 cp936）。
   可靠做法是在 bash 侧或 `cmd /c` 侧重定向到文件，再用 read 工具读。**下采样也要交叉**：两边交替跑，才能把"网络时段漂移"和"OS 差异"分开（`dl_dist.ps1` 就是这么做的）。

## 又踩到的四个坑（写下来免得重犯）

1. **Windows git 的 `core.autocrlf` 系统默认是 `true`**（Git for Windows 的安装默认）。做行尾实验前必须显式钉住，
   否则 CRLF 会被静默归一化，实验前提直接错掉。
2. **别把函数命名成 `Diff`、`Sort`、`Where` 这类名字**——它们是 PowerShell 内置别名（`Diff` = `Compare-Object`），
   会被静默遮蔽，表现为莫名其妙的"缺少参数"。
3. **`[IO.File]::WriteAllText` 用相对路径时按 .NET 进程 CWD 解析，而 `Push-Location` 不更新它**
   → 测试文件会被写进**启动时的那个目录**。本次真发生过：`a.py`/`b.py`/`c.sh` 被写进了真实仓库根目录（已清理）。
   规矩：脚本里凡是写文件，**一律用绝对路径**。
4. **PowerShell 里 `\"` 不是转义**（要用 `` `" ``）。在 PowerShell 里拼 bash 命令字符串必然翻车——
   把 bash 部分抽成独立 `.sh`，PowerShell 只传参数（`dl_once.sh` 就是这么拆出来的）。

## 已知缺项（有意不测）

- **GUI/X 只验到"窗口被 X 服务器接受并映射"**（`map_state=2`），没有验证渲染质量与键盘/输入法；
- **`sudo` 需密码**，故未安装 `x11-apps`/`python3-tk` 等可用于更完整 GUI 测试的包；
- 电池中的路径是本机实际路径（`C:\Users\typ\...`），换机需改；这与仓库其余文档的口径一致。
