@echo off
rem 卸载开机自启：删掉启动文件夹里由安装脚本生成的那个文件。

set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "F=%STARTUP%\改图服务_自启.cmd"

if exist "%F%" (
  del "%F%"
  echo 已删除： %F%
) else (
  echo 未找到自启文件，可能本来就没安装：
  echo   %F%
)
echo.
echo 注意：这只取消开机自启，不会停止当前正在运行的服务。
echo 要停服务，直接关掉那个改图服务的黑窗口。
pause
