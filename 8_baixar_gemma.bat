@echo off
chcp 65001 >nul
title Baixando a IA Gemma 3 12B
set OLL=%LOCALAPPDATA%\Programs\Ollama\ollama.exe
if not exist "%OLL%" set OLL=ollama
echo Baixando o Gemma 3 12B (uns 8 GB). Pode demorar alguns minutos...
echo.
"%OLL%" pull gemma3:12b
echo.
echo Testando...
"%OLL%" run gemma3:12b "Responda so: ok"
echo.
echo Pronto! Feche e abra o Jon: ele passa a usar o Gemma 3 12B sozinho.
pause
