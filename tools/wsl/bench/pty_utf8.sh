#!/usr/bin/env bash
# 验证集成终端所依赖的"PTY 层"是否原样承载多字节中文
# 原理：VS Code 集成终端 <-> 远端 shell 之间就是一个 PTY。用 script(1) 造一个真 PTY，
# 把中文写进去再取回，逐字节比对——这能验证数据通路，但不能验证 IME（那是 UI 层）。
set -uo pipefail

SENT='中文测试：文件台账 ①②③ — 测试'
TMP=$(mktemp)

printf '%s\n' "$SENT" > "$TMP.expect"
# -q 静默 -e 执行命令 -c 用 sh -c；输出到 /dev/null 表示不做类型记录
script -qec "cat '$TMP.expect'" /dev/null > "$TMP.got" 2>&1

echo "写入(期望)  : $(cat "$TMP.expect")"
echo "PTY 取回    : $(cat "$TMP.got")"
# PTY 的行规程会做 ONLCR（LF -> CRLF），这是终端固有行为，不是编码损失。
# 故比较前先归一化行尾，再逐字节比对正文。
sed -e 's/\r$//' "$TMP.got" > "$TMP.got.norm"
echo "字节数      : expect=$(stat -c%s "$TMP.expect")  got=$(stat -c%s "$TMP.got")  got(去 CR 后)=$(stat -c%s "$TMP.got.norm")"
if cmp -s "$TMP.expect" "$TMP.got"; then
    echo "PTY 往返    : 逐字节一致 ✓（连 ONLCR 都没发生）"
elif cmp -s "$TMP.expect" "$TMP.got.norm"; then
    echo "PTY 往返    : 正文逐字节一致 ✓；唯一差异是 PTY 的 ONLCR（LF→CRLF）——终端固有行为，非编码损失"
else
    echo "PTY 往返    : 有真实差异（不是 ONLCR 能解释的）"
    echo "  expect hex: $(xxd -p "$TMP.expect" | head -2 | tr '\n' ' ')"
    echo "  got    hex: $(xxd -p "$TMP.got.norm" | head -2 | tr '\n' ' ')"
fi

echo "--- 终端相关环境（远端 shell 实际看到的）---"
echo "LANG=${LANG:-未设置}  LC_ALL=${LC_ALL:-未设置}"
echo "charatmap=$(locale charmap 2>/dev/null)"
echo "TERM=${TERM:-未设置}  COLORTERM=${COLORTERM:-未设置}"
echo "登录 shell=$(getent passwd "$USER" | cut -d: -f7)"
rm -f "$TMP" "$TMP.expect" "$TMP.got"
