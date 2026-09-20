@echo off
setlocal
cd /d "%~dp0"

python -m discord_companion.bot
set EXITCODE=%ERRORLEVEL%

echo.
if not "%EXITCODE%"=="0" (
    echo Finch stopped with exit code %EXITCODE%.
) else (
    echo Finch stopped.
)
pause
exit /b %EXITCODE%
