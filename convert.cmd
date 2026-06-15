@echo off
setlocal EnableExtensions

if "%~1"=="" (
    python "%~dp0convert.py"
    exit /b 1
)

if "%~2"=="" (
    python "%~dp0convert.py"
    exit /b 1
)

if "%~3"=="" (
    python "%~dp0convert.py" "%~1" "%~2"
    exit /b %ERRORLEVEL%
)

python "%~dp0convert.py" "%~1" "%~2" "%~3"
exit /b %ERRORLEVEL%
