@echo off
chcp 65001 >nul
rem Builds ONE APK with every character listed in combo.txt (edit combo.txt: one Update folder name per line, e.g. MacuriUpdate).
rem Compile UN SEUL APK avec tous les personnages de combo.txt (un nom de dossier Update par ligne).
wsl.exe --status >nul 2>&1 || (echo Install WSL first& pause & exit /b 1)
for /f "usebackq delims=" %%p in (`wsl wslpath -a "%~dp0..\Kit\scripts"`) do set P=%%p
if not exist "%~dp0out" mkdir "%~dp0out"
for /f "usebackq delims=" %%p in (`wsl wslpath -a "%~dp0out"`) do set O=%%p
for /f "usebackq delims=" %%p in (`wsl wslpath -a "%~dp0combo.txt"`) do set C=%%p
wsl bash "%P%/run_combo.sh" "%C%" "%O%"
echo.
echo Done. Results are in the out folder.
pause
