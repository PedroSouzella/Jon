@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Instalando as bibliotecas do Jon (Python 3.12)...
py -3.12 -m pip install --upgrade pip
py -3.12 -m pip install SpeechRecognition sounddevice numpy keyboard pyperclip pygetwindow spotipy customtkinter psutil pillow edge-tts
echo.
echo Criando o atalho "Jon" na Area de Trabalho...
py -3.12 atalhos.py
echo.
echo Pronto! Abra pelo atalho "Jon" na Area de Trabalho.
pause
