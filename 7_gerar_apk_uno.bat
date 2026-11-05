@echo off
chcp 65001 >nul
title Gerador de APK — JON OS Fiat Uno 9"
cd /d "%~dp0"

set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist "%PY%" set "PY=python"

"%PY%" "%~dp0android_uno_9p\compilar_apk.py"
echo.
pause
