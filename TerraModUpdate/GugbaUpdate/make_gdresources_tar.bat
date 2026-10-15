@echo off
setlocal
rem Packs ONLY the new images of gdresources_new into gdresources_new.tar (gdresources\data_u2017\...). Nothing of yours is read or changed.
set "KIT=%~dp0"
set "N=%KIT%gdresources_new"
set "P=%KIT%_pack\gdresources\data_u2017"
set FOUND=0
for %%S in (Pieces Illust BuddyImages BuddyThumbs Profile) do if exist "%N%\%%S\*.bin" set FOUND=1
if "%FOUND%"=="0" (
  echo There are no new image files for this character in gdresources_new. The images you already installed are still valid.
  echo  gdresources_new 
  pause & exit /b 0
)
if exist "%KIT%_pack" rmdir /s /q "%KIT%_pack"
mkdir "%P%\android\Pieces" "%P%\android\Illust" "%P%\android\BuddyImages" "%P%\android\BuddyThumbs" "%P%\Profile" || goto :fail
if exist "%N%\Pieces\*.bin"      copy /y "%N%\Pieces\*.bin"      "%P%\android\Pieces\"      >nul
if exist "%N%\Illust\*.bin"      copy /y "%N%\Illust\*.bin"      "%P%\android\Illust\"      >nul
if exist "%N%\BuddyImages\*.bin" copy /y "%N%\BuddyImages\*.bin" "%P%\android\BuddyImages\" >nul
if exist "%N%\BuddyThumbs\*.bin" copy /y "%N%\BuddyThumbs\*.bin" "%P%\android\BuddyThumbs\" >nul
if exist "%N%\Profile\*.bin"     copy /y "%N%\Profile\*.bin"     "%P%\Profile\"             >nul
if exist "%KIT%gdresources_new.tar" del /q "%KIT%gdresources_new.tar"
tar -cf "%KIT%gdresources_new.tar" -C "%KIT%_pack" gdresources || goto :fail
rmdir /s /q "%KIT%_pack"
echo.
echo Done: %KIT%gdresources_new.tar
pause
exit /b 0
:fail
echo FAILED
if exist "%KIT%_pack" rmdir /s /q "%KIT%_pack"
pause
exit /b 1
