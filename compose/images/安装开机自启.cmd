@echo off
rem 安装「登录后自动启动改图服务」—— 放进当前用户的启动文件夹。
rem 不需要管理员权限。撤销：双击同目录的「卸载开机自启.cmd」，或删掉启动文件夹里那个文件。

set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "TARGET=%~dp0启动改图.cmd"

if not exist "%TARGET%" (
  echo [失败] 找不到启动器：%TARGET%
  pause
  exit /b 1
)

echo 将写入： %STARTUP%\改图服务_自启.cmd
echo 指向：   %TARGET%
echo.

> "%STARTUP%\改图服务_自启.cmd" echo @echo off
>> "%STARTUP%\改图服务_自启.cmd" echo rem 由「安装开机自启.cmd」生成 —— 删除本文件即取消开机自启。
>> "%STARTUP%\改图服务_自启.cmd" echo start "" /min "%TARGET%"

if errorlevel 1 (
  echo [失败] 写入启动文件夹失败。
  pause
  exit /b 1
)

echo 已安装。下次登录 Windows 后，改图服务会自动以最小化窗口启动。
echo.
echo 现在就启动一次吗？回车即启动（关掉那个窗口即可停止）。
pause >nul
start "" /min "%TARGET%"
