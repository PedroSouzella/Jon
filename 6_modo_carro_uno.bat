@echo off
chcp 65001 >nul
title JON OS // Central Multimidia 9" Fiat Uno 2006
cd /d "%~dp0"

set "PYW=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist "%PY%" set "PY=python"

echo ========================================================
echo   ◆ J O N   O S — FIAT UNO 2006 (CENTRAL 9 POLEGADAS)
echo ========================================================
echo.
echo [1/2] Iniciando servidor e voz JARVIS do Jon...
netstat -ano | findstr ":8765 " | findstr "LISTENING" >nul 2>nul
if %errorlevel% neq 0 (
    if exist "%PYW%" (
        start "" "%PYW%" "%~dp0app.pyw"
    ) else (
        start "Servidor Jon Car OS" /min "%PY%" "%~dp0web_jon.py"
    )
    timeout /t 3 /nobreak >nul
)

echo [2/2] Abrindo Central Nativa 9" (Sem bordas + Autoplay JARVIS)...
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --app="http://127.0.0.1:8765/carro" --autoplay-policy=no-user-gesture-required --window-size=1280,720
    exit /b
)

if exist "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" (
    start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --app="http://127.0.0.1:8765/carro" --autoplay-policy=no-user-gesture-required --window-size=1280,720
    exit /b
)

start "" "http://127.0.0.1:8765/carro"
