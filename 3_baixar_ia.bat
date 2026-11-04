@echo off
chcp 65001 >nul
title Baixando a IA local
set OLL=%LOCALAPPDATA%\Programs\Ollama\ollama.exe
if not exist "%OLL%" set OLL=ollama
echo Baixando o modelo de IA (qwen3.5:4b, uns 3,4 GB). Pode demorar alguns minutos...
"%OLL%" pull qwen3.5:4b
echo.
echo Testando...
"%OLL%" run qwen3.5:4b "Responda so: ok" --think=false
echo.
echo Pronto! Pode fechar esta janela e reabrir o Assistente de Voz.
pause
