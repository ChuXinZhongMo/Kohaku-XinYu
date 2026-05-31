@echo off
chcp 65001 >nul
setlocal

set "ROOT=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%XinYu.ps1" verify qq
set "EXITCODE=%ERRORLEVEL%"

if not "%XINYU_NO_PAUSE%"=="1" (
    echo.
    pause
)

exit /b %EXITCODE%
