@echo off
chcp 65001 >nul
title Assistente de Voz
cd /d "%~dp0"
py -3.12 assistente_voz.py
pause
