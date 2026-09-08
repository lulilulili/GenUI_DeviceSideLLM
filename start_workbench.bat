@echo off
title GenUI v2 Workbench Launcher
cd /d "%~dp0"
set "SYS32=%SystemRoot%\System32"

echo ==============================================
echo   GenUI v2 端侧工作台 - 一键启动
echo ==============================================

rem ---- [1/3] 确保 Ollama 在运行 ----
"%SYS32%\curl.exe" -s --max-time 3 http://127.0.0.1:11434/api/version >nul 2>&1
if errorlevel 1 (
    echo [1/3] Ollama 未运行，正在启动...
    start "" "%LOCALAPPDATA%\Programs\Ollama\ollama app.exe"
    "%SYS32%\ping.exe" -n 7 127.0.0.1 >nul
) else (
    echo [1/3] Ollama 已在运行
)

rem ---- 检查默认模型 ----
"%SYS32%\curl.exe" -s --max-time 5 http://127.0.0.1:11434/api/tags | "%SYS32%\findstr.exe" /C:"qwen2.5:3b" >nul 2>&1
if errorlevel 1 (
    echo [提示] 未检测到 qwen2.5:3b，请先执行: ollama pull qwen2.5:3b
) else (
    echo       模型 qwen2.5:3b 已就绪
)

rem ---- [2/3] 启动工作台服务（已在运行则复用） ----
"%SYS32%\netstat.exe" -ano | "%SYS32%\findstr.exe" /C:":8766 " | "%SYS32%\findstr.exe" LISTENING >nul 2>&1
if errorlevel 1 (
    echo [2/3] 启动工作台 http://127.0.0.1:8766 ...
    start "GenUI v2 Workbench" /min cmd /c "cd /d "%~dp0" && python -m genui_v2.workbench"
    "%SYS32%\ping.exe" -n 3 127.0.0.1 >nul
) else (
    echo [2/3] 工作台已在运行
)

rem ---- [3/3] 打开浏览器 ----
echo [3/3] 打开浏览器...
start "" "http://127.0.0.1:8766/"

echo.
echo 完成。演示无模型时可在页面里把 Provider 切到 Mock。
echo 不再使用时关掉标题为 "GenUI v2 Workbench" 的最小化窗口即可。
"%SYS32%\ping.exe" -n 6 127.0.0.1 >nul
exit
