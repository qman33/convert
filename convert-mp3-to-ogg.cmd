@echo off
setlocal EnableExtensions

if "%~1"=="" (
    echo Usage: convert-mp3-to-ogg ^<path\to\file.mp3^>
    exit /b 1
)

python "%~dp0convert_mp3_to_ogg.py" "%~1"
exit /b %ERRORLEVEL%
