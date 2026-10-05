# Windows+WSL2 搭配实测 · Windows 侧电池（与 bench_wsl.sh 对称，同代码同样本）
param(
    # 大样本输入图（约几十 MB 的 jpg/png）；不传则报错退出。
    [string]$Big = '',
    # Python 解释器；默认取 PATH 上的 python，也可指定完整路径。
    [string]$Python = 'python'
)
$ErrorActionPreference = 'Continue'
if (-not $Big -or -not (Test-Path $Big)) {
    Write-Error '用法: ./bench_win.ps1 -Big <大图路径>（用 -Big 指定一张几十 MB 的样本图）'
    exit 1
}
$W   = Join-Path $env:TEMP 'mantu_g5'
$L   = Join-Path $W 'bench_win'
$BIG = $Big
New-Item -ItemType Directory -Force -Path $L | Out-Null

function Best3([scriptblock]$sb) {
    $best = $null
    1..3 | ForEach-Object {
        $sw = [Diagnostics.Stopwatch]::StartNew()
        & $sb | Out-Null
        $sw.Stop()
        $s = $sw.Elapsed.TotalSeconds
        if ($null -eq $best -or $s -lt $best) { $best = $s }
    }
    return [math]::Round($best, 3)
}

Write-Output '== A 环境 =='
$os = Get-CimInstance Win32_OperatingSystem
"os=$($os.Caption) build $($os.BuildNumber)"
"python=$(& $Python -V 2>&1)"
"cpu=$((Get-CimInstance Win32_Processor | Select-Object -First 1).Name)"
"cpu_cores=$((Get-CimInstance Win32_Processor | Measure-Object NumberOfLogicalProcessors -Sum).Sum)"
"mem_total_mb=$([math]::Round($os.TotalVisibleMemorySize/1024))"
"mem_free_mb=$([math]::Round($os.FreePhysicalMemory/1024))"
"disk_avail_c=$([math]::Round((Get-PSDrive C).Free/1GB,1)) GB"

Write-Output ''
Write-Output '== B CPU（同一段纯 Python 整数循环 3e6 次，3 次取最好）=='
$sw = [Diagnostics.Stopwatch]::StartNew()
& $Python (Join-Path $W 'cpu_loop.py')
$sw.Stop()
"cpu_pyloop_win=$( & $Python (Join-Path $W 'cpu_loop.py') )s  (含解释器启动 $( [math]::Round($sw.Elapsed.TotalSeconds,3) )s)"

Write-Output ''
Write-Output '== C 磁盘：顺序读同一份 18MB PNG =='
$sha = [Security.Cryptography.SHA256]::Create()
$readBig = { $fs = [IO.File]::OpenRead($BIG); $null = $sha.ComputeHash($fs); $fs.Close() }
"seqread_bigfile_native=$(Best3 $readBig)s"

Write-Output '== C 磁盘：顺序写 64MB =='
$buf = New-Object byte[] (1MB)
$write64 = {
    $fs = [IO.File]::Create((Join-Path $L 'big.bin'))
    for ($i = 0; $i -lt 64; $i++) { $fs.Write($buf, 0, $buf.Length) }
    $fs.Flush($true); $fs.Close()
}
"seqwrite_64mb_native=$(Best3 $write64)s"

Write-Output '== C 磁盘：500 个 1KB 小文件（创建 / 读取）=='
$data = New-Object byte[] 1024
$mkSmall = {
    $d = Join-Path $L 'small'
    if (Test-Path $d) { Remove-Item $d -Recurse -Force }
    $null = New-Item -ItemType Directory -Path $d
    for ($i = 1; $i -le 500; $i++) { [IO.File]::WriteAllBytes((Join-Path $d "f$i.txt"), $data) }
}
$rdSmall = {
    foreach ($f in [IO.Directory]::GetFiles((Join-Path $L 'small'))) { $null = [IO.File]::ReadAllBytes($f) }
}
"smallfiles_create_500_native=$(Best3 $mkSmall)s"
"smallfiles_read_500_native=$(Best3 $rdSmall)s"

Write-Output ''
Write-Output '== D 网络：RTT（5 次取均值）=='
foreach ($h in @('image-direct.geiliapi.com', 'pypi.tuna.tsinghua.edu.cn')) {
    $r = Test-Connection -TargetName $h -Count 5 -ErrorAction SilentlyContinue
    if ($r) {
        $avg = ($r | Where-Object { $_.Latency -ne $null } | Measure-Object Latency -Average).Average
        "rtt_avg_ms[$h]=$([math]::Round($avg,1))"
    } else { "rtt_avg_ms[$h]=失败" }
}

Write-Output '== D 网络：下载吞吐（与 WSL 侧同一个绝对 URL）=='
$url = 'https://pypi.tuna.tsinghua.edu.cn/packages/84/21/a35af28dcc61f37ed850a2d64c65c701321dfbf25085e469d5559360cbbf/pillow-12.3.0-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl'
$dl = { & curl.exe -s -o NUL --max-time 90 $url }
$b = Best3 $dl
"download_6.9MB_best=${b}s"
"download_MBps=$([math]::Round(6.9/$b,1))"

Write-Output ''
Write-Output '== E GPU =='
$smi = & nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>&1
"smi=$smi"
"dlcv_torch=$(& D:\Anconda3\envs\dl-cv\python.exe -c "import torch;print(torch.__version__, torch.cuda.is_available())" 2>&1)"

Write-Output ''
Write-Output '== F GUI / X =='
'windows_is_display_host=N/A（Windows 本身就是显示宿主）'

Write-Output ''
Write-Output '== G 跨边界编码往返 =='
$str = '中文哨兵：文件台账 ①②③ — ZWSP测试'
[IO.File]::WriteAllText((Join-Path $W 'enc_win2wsl.txt'), $str + "`n", (New-Object Text.UTF8Encoding($false)))
"win_wrote=UTF-8(no BOM)"
$wslFile = Join-Path $W 'enc_wsl2win.txt'
if (Test-Path $wslFile) {
    $got = (Get-Content $wslFile -Encoding utf8 -TotalCount 1)
    "read_from_wsl=$got"
    "match=$($got -eq $str)"
    "bytes_head=$(($bytes = [IO.File]::ReadAllBytes($wslFile))[0..8] -join ',')"
} else { 'read_from_wsl=（WSL 侧文件尚未生成）' }

Write-Output 'DONE_WIN'
