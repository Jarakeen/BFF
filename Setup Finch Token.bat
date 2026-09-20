@echo off
setlocal
cd /d "%~dp0"

python -m discord_companion.configure_token
set EXITCODE=%ERRORLEVEL%

echo.
if not "%EXITCODE%"=="0" (
    echo Finch token setup failed with exit code %EXITCODE%.
) else (
    echo Finch token setup completed.
)
pause
exit /b %EXITCODE%
