@echo off
chcp 65001 >nul
wsl.exe --status >nul 2>&1 || (echo Install WSL first: PowerShell as administrator, wsl --install, reboot.& pause & exit /b 1)
for /f "usebackq delims=" %%p in (`wsl wslpath -a "%~dp0..\Kit\scripts"`) do set P=%%p
if not exist "%~dp0out" mkdir "%~dp0out"
for /f "usebackq delims=" %%p in (`wsl wslpath -a "%~dp0out"`) do set O=%%p

wsl bash "%P%/run.sh" "%O%" YapkarUpdate
echo.
echo Done. Results are in the out folder.
pause
