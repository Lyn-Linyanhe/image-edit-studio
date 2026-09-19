@echo off
rem 本地改图服务启动器 —— 双击本文件即可。
rem 关掉这个黑窗口 = 停止服务。日志追加写入同目录的 server.log。

cd /d "%~dp0"

echo ============================================================
echo   本地改图服务
echo   访问地址： http://127.0.0.1:8000
echo   停止：在本窗口按 Ctrl+C，或直接关闭窗口
echo   日志： server.log（本目录）
echo ============================================================
echo.

"C:\Python314\python.exe" mask_edit_app.py --port 8000 --log server.log

if errorlevel 1 (
  echo.
  echo [启动失败] 退出码 %errorlevel%
  echo 常见原因：8000 端口已被占用（先关掉另一个改图窗口），
  echo           或 python 不在这个路径：C:\Python314\python.exe
  echo.
  pause
)
