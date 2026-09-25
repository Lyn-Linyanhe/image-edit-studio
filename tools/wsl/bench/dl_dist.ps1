# 下载吞吐实验：交叉采样取分布 + 协议对照（HTTP/2 vs HTTP/1.1）
#
# 为什么交叉：单向连跑 10 次会把"网络时段漂移"误判成"OS 差异"；两边交替采样可以把漂移摊平。
# 与 WSL 侧的交互全部走 tools/wsl/bench/dl_once.sh（不在 PowerShell 里拼 bash 字符串——
# 上一版就死在 PowerShell 的 \" 不是转义上）。
$ErrorActionPreference = 'Continue'
$SIZE = 6.9   # MB（该轮子大小）
$URL = 'https://pypi.tuna.tsinghua.edu.cn/packages/84/21/a35af28dcc61f37ed850a2d64c65c701321dfbf25085e469d5559360cbbf/pillow-12.3.0-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl'
$DL_ONCE = '/mnt/c/Users/typ/Desktop/mantu/tools/wsl/bench/dl_once.sh'

function TimeWin([string]$extra = '') {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    if ($extra) { & curl.exe -s $extra -o NUL --max-time 120 $URL | Out-Null }
    else        { & curl.exe -s       -o NUL --max-time 120 $URL | Out-Null }
    $sw.Stop()
    return [math]::Round($sw.Elapsed.TotalSeconds, 3)
}
function TimeWsl([string]$extra = '') {
    $r = if ($extra) { wsl.exe -d Ubuntu-24.04 -e bash $DL_ONCE $extra 2>$null }
         else        { wsl.exe -d Ubuntu-24.04 -e bash $DL_ONCE        2>$null }
    return [double](($r | Where-Object { $_ -match '^[0-9.]+$' } | Select-Object -Last 1))
}
function Stats([double[]]$xs, [string]$label) {
    $s = @($xs | Sort-Object)
    if ($s.Count -eq 0) { Write-Output "$label : 无样本"; return }
    $med = $s[[int][math]::Floor($s.Count / 2)]
    "{0,-24} n={1,-3} min={2,6:N3}s  中位={3,6:N3}s  max={4,6:N3}s   中位速率={5,5:N1} MB/s" -f `
        $label, $s.Count, $s[0], $med, $s[-1], ($SIZE / $med)
}

Write-Output "=== 两侧 curl 能力（决定协议对照是否有意义）==="
$wv = ((& curl.exe -V 2>&1) -join ' ')
Write-Output ("Windows curl : " + (($wv -split "`n")[0]).Trim())
Write-Output ("  HTTP2 支持 : " + $(if ($wv -match 'HTTP2') { '有' } else { '无' }))
$lv = ((wsl.exe -d Ubuntu-24.04 -e curl -V 2>$null) -join ' ')
Write-Output ("WSL curl     : " + (($lv -split "`n")[0]).Trim())
Write-Output ("  HTTP2 支持 : " + $(if ($lv -match 'HTTP2') { '有' } else { '无' }))
Write-Output ""

Write-Output "=== A 默认协议，10 轮交叉采样 ==="
$win = @(); $wsl = @()
for ($i = 1; $i -le 10; $i++) {
    $wsl += TimeWsl
    $win += TimeWin
    Write-Output ("  round {0,2}:  WSL={1,7:N3}s   Windows={2,7:N3}s" -f $i, $wsl[-1], $win[-1])
}
Stats $win 'Windows（默认协议）'
Stats $wsl 'WSL（默认协议）'

Write-Output ""
Write-Output "=== B 两边都强制 HTTP/1.1，6 轮交叉（隔离"协议"变量）==="
$win11 = @(); $wsl11 = @()
for ($i = 1; $i -le 6; $i++) {
    $wsl11 += TimeWsl '--http1.1'
    $win11 += TimeWin '--http1.1'
    Write-Output ("  round {0,2}:  WSL={1,7:N3}s   Windows={2,7:N3}s" -f $i, $wsl11[-1], $win11[-1])
}
Stats $win11 'Windows（强制 1.1）'
Stats $wsl11 'WSL（强制 1.1）'
