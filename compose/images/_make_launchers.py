"""生成改图服务的三个 .cmd（全部按 cp936 写出，避免 cmd 里中文乱码）。

开机自启用【启动文件夹】而不是计划任务，原因（已实测）：
    schtasks /create ... /sc onlogon  在本机非管理员下直接 "Access is denied"，
    而启动文件夹是每用户的、不需要提权、删除一个文件即可撤销。
"""
from pathlib import Path
import os as _os
_MANTU_ROOT_STR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *([".."] * 2)))

DIR = Path(rf"{_MANTU_ROOT_STR}\compose\images")
PY = r"C:\Python314\python.exe"
STARTUP_NAME = "改图服务_自启.cmd"

START = """@echo off
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

"%PYEXE%" mask_edit_app.py --port 8000 --log server.log

if errorlevel 1 (
  echo.
  echo [启动失败] 退出码 %errorlevel%
  echo 常见原因：8000 端口已被占用（先关掉另一个改图窗口），
  echo           或 python 不在这个路径：%PYEXE%
  echo.
  pause
)
""".replace("%PYEXE%", PY)

INSTALL = """@echo off
rem 安装「登录后自动启动改图服务」—— 放进当前用户的启动文件夹。
rem 不需要管理员权限。撤销：双击同目录的「卸载开机自启.cmd」，或删掉启动文件夹里那个文件。

set "STARTUP=%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"
set "TARGET=%~dp0启动改图.cmd"

if not exist "%TARGET%" (
  echo [失败] 找不到启动器：%TARGET%
  pause
  exit /b 1
)

echo 将写入： %STARTUP%\\%STARTUPNAME%
echo 指向：   %TARGET%
echo.

> "%STARTUP%\\%STARTUPNAME%" echo @echo off
>> "%STARTUP%\\%STARTUPNAME%" echo rem 由「安装开机自启.cmd」生成 —— 删除本文件即取消开机自启。
>> "%STARTUP%\\%STARTUPNAME%" echo start "" /min "%TARGET%"

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
""".replace("%STARTUPNAME%", STARTUP_NAME)

UNINSTALL = """@echo off
rem 卸载开机自启：删掉启动文件夹里由安装脚本生成的那个文件。

set "STARTUP=%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"
set "F=%STARTUP%\\%STARTUPNAME%"

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
""".replace("%STARTUPNAME%", STARTUP_NAME)

for name, body in [("启动改图.cmd", START),
                   ("安装开机自启.cmd", INSTALL),
                   ("卸载开机自启.cmd", UNINSTALL)]:
    p = DIR / name
    p.write_bytes(body.replace("\n", "\r\n").encode("cp936"))
    print(f"  {name}  ({p.stat().st_size} bytes, cp936)")
