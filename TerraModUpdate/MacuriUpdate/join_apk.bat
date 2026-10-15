@echo off
setlocal
rem Joins every split file set NAME.partNN found in this folder, release\, out\ and ..\Kit\input\ into NAME, then shows SHA256. The parts are not changed.
for %%D in ("%~dp0" "%~dp0release\" "%~dp0out\" "%~dp0..\Kit\input\") do (
  for %%F in ("%%~D*.part00") do (
    if exist "%%~dpnF.part00" (
      echo Joining %%~nF ...
      copy /y /b "%%~dpnF.part*" "%%~dpnF" >nul
      certutil -hashfile "%%~dpnF" SHA256
    )
  )
)
if exist "%~dp0release\SHA256.txt" (echo Expected: & type "%~dp0release\SHA256.txt")
pause
