# 行尾实验（修订版 2）：在**临时仓库**里测 "files.eol / .gitattributes 能否消除整文件假 diff"
#
# 踩过的三个坑（都写在这里，免得再犯）：
#   ① 没钉 core.autocrlf —— Git for Windows 系统默认是 true，会把 CRLF 归一化，实验前提就错了；
#   ② 函数叫 Diff —— 与 PowerShell 内置别名 Compare-Object 撞名，调用直接报参数缺失；
#   ③ [IO.File]::WriteAllText 用**相对路径**时按 .NET 进程 CWD 解析，而 Push-Location 不更新它
#      → 测试文件被写进了工作区根目录（已清理）。本版一律用绝对路径。
$ErrorActionPreference = 'Continue'
$root = Join-Path $env:TEMP ('eol_probe_' + [Guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Path $root | Out-Null

function Say([string]$s) { Write-Output $s }
function WCrlf([string]$p, [string[]]$l) { [IO.File]::WriteAllText($p, (($l -join "`r`n") + "`r`n"), (New-Object Text.UTF8Encoding($false))) }
function WLf([string]$p, [string[]]$l)   { [IO.File]::WriteAllText($p, (($l -join "`n") + "`n"), (New-Object Text.UTF8Encoding($false))) }
function Commit([string]$msg) {
    $o = git -C $root -c user.email=b@b -c user.name=b commit -m $msg 2>&1
    if ($LASTEXITCODE -ne 0) { Say "  !! commit 失败: $o" }
    Say ("  （已跟踪文件数: {0}）" -f (git -C $root ls-files | Measure-Object).Count)
}
function ShowDiff([string]$label) {
    $n = git -C $root diff --numstat 2>&1
    if (-not "$n".Trim()) { Say ("  {0,-46} -> 无差异（干净）" -f $label) }
    else { Say ("  {0,-46} -> {1}" -f $label, "$n".Trim()) }
}

$A = Join-Path $root 'a.py'
$B = Join-Path $root 'b.py'
$C = Join-Path $root 'c.sh'
$GA = Join-Path $root '.gitattributes'
$L = @('# test', 'def f(x):', '    return x + 1', '', 'print(f(1))')

git -C $root init -q
git -C $root config --local core.autocrlf false
git -C $root config --local core.eol native
Say "临时仓库 core.autocrlf = $(git -C $root config core.autocrlf)"
Say "系统级 core.autocrlf = $(git config --system core.autocrlf 2>$null)  ← Git for Windows 默认常为 true（坑①）"
Say ""

'* -text' | Set-Content -NoNewline $GA
WCrlf $A $L
git -C $root add -A
Commit 'base'
Say ""

Say "【对照1】现状策略 * -text：编辑器把 CRLF 存成 LF"
WLf $A $L
ShowDiff '* -text + 存成 LF'

Say "【对照2】同一基线：编辑器保持 CRLF（= files.eol 正确时的行为）"
git -C $root checkout -q -- a.py
ShowDiff '保持 CRLF'

Say "【对照3】策略换成 * text=auto eol=crlf，再存成 LF"
'* text=auto eol=crlf' | Set-Content -NoNewline $GA
git -C $root add -A
Commit 'switch to text=auto eol=crlf'
WLf $A $L
ShowDiff '* text=auto eol=crlf + 存成 LF'

Say "【对照4】混合行尾（.py 要 CRLF、.sh 必须 LF）能否一刀切"
'* text=auto' | Set-Content -NoNewline $GA
'*.sh text eol=lf' | Add-Content -NoNewline $GA
WCrlf $B $L
WLf $C "#!/usr/bin/env bash`necho hi"
git -C $root add -A
Commit 'mixed policy'
Say "  b.py 索引/工作区行尾: $(git -C $root ls-files --eol b.py)"
Say "  c.sh 索引/工作区行尾: $(git -C $root ls-files --eol c.sh)"
WLf $B $L
ShowDiff '* text=auto + *.sh eol=lf：.py 存成 LF'

Say ""
Say "=== 真实仓库当前实际行尾（抽样，含新增的 LF 文件）==="
git -C 'C:<工作区>' ls-files --eol style-distill/round_lib/run_round.py style-distill/round_lib/acceptance.py tools/wsl/wslrun.sh

Remove-Item $root -Recurse -Force
Say "（临时仓库已删除）"
