@echo off
setlocal EnableExtensions

if "%~3"=="" (
    python "%~dp0convert.py"
    exit /b 1
)

python "%~dp0convert.py" "%~1" "%~2" "%~3"
exit /b %ERRORLEVEL%
