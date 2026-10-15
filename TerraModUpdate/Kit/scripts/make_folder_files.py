"""Writes the per-folder helper files (build.bat, join_apk.bat, make_gdresources_tar.bat, README.txt) of every Update folder.  Run from anywhere:
python3 make_folder_files.py <TerraModUpdate root>"""
import os, sys

root = sys.argv[1]
CRLF = lambda s: s.replace("\r\n", "\n").replace("\n", "\r\n")

def w(path, text, crlf=True):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(CRLF(text) if crlf else text)

BUILD_BAT = r"""@echo off
chcp 65001 >nul
rem Builds %NAME% (game APK + Host APK) -> out\   /   打包 %NAME%（遊戲 APK + Host APK）到 out\   /   Compile %NAME% -> out\
wsl.exe --status >nul 2>&1 || (echo Install WSL first: PowerShell as administrator, wsl --install, reboot. / 請先安裝 WSL: 以系統管理員開啟 PowerShell 輸入 wsl --install 後重開機 & pause & exit /b 1)
for /f "usebackq delims=" %%p in (`wsl wslpath -a "%~dp0..\Kit\scripts"`) do set P=%%p
if not exist "%~dp0out" mkdir "%~dp0out"
for /f "usebackq delims=" %%p in (`wsl wslpath -a "%~dp0out"`) do set O=%%p
%FOLDERS_SET%
wsl bash "%P%/run.sh" "%O%" %FOLDERS%
echo.
echo Done. Results are in the out folder. / 完成，成品在 out 資料夾。
pause
"""

COMBO_BAT = r"""@echo off
chcp 65001 >nul
rem Builds ONE APK with every character listed in combo.txt (edit combo.txt: one Update folder name per line, e.g. MacuriUpdate).
rem 把 combo.txt 內列出的角色全部打進同一個 APK（編輯 combo.txt：每行一個 Update 資料夾名稱，例如 MacuriUpdate）。
rem Compile UN SEUL APK avec tous les personnages de combo.txt (un nom de dossier Update par ligne).
wsl.exe --status >nul 2>&1 || (echo Install WSL first / 請先安裝 WSL & pause & exit /b 1)
for /f "usebackq delims=" %%p in (`wsl wslpath -a "%~dp0..\Kit\scripts"`) do set P=%%p
if not exist "%~dp0out" mkdir "%~dp0out"
for /f "usebackq delims=" %%p in (`wsl wslpath -a "%~dp0out"`) do set O=%%p
for /f "usebackq delims=" %%p in (`wsl wslpath -a "%~dp0combo.txt"`) do set C=%%p
wsl bash "%P%/run_combo.sh" "%C%" "%O%"
echo.
echo Done. Results are in the out folder. / 完成，成品在 out 資料夾。
pause
"""

JOIN_BAT = r"""@echo off
setlocal
rem Joins every split file set NAME.partNN found in this folder, release\, out\ and ..\Kit\input\ into NAME, then shows SHA256. The parts are not changed.
rem 合併本資料夾、release\、out\、..\Kit\input\ 內所有「名稱.partNN」分割檔成完整檔並顯示 SHA256，不修改分割檔。
rem Assemble tous les fichiers « nom.partNN » de ce dossier, release\, out\ et ..\Kit\input\ en « nom » et affiche le SHA256 ; les parties ne sont pas modifiées.
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
"""

TAR_BAT = r"""@echo off
setlocal
rem Packs ONLY the new images of gdresources_new into gdresources_new.tar (gdresources\data_u2017\...). Nothing of yours is read or changed.
rem 只把 gdresources_new 內的新圖打成 gdresources_new.tar（結構 gdresources\data_u2017\...），不讀取也不修改你的任何原檔。
rem Emballe UNIQUEMENT les nouvelles images de gdresources_new dans gdresources_new.tar ; aucun de vos fichiers n'est lu ni modifié.
set "KIT=%~dp0"
set "N=%KIT%gdresources_new"
set "P=%KIT%_pack\gdresources\data_u2017"
set FOUND=0
for %%S in (Pieces Illust BuddyImages BuddyThumbs Profile) do if exist "%N%\%%S\*.bin" set FOUND=1
if "%FOUND%"=="0" (
  echo There are no new image files for this character in gdresources_new. The images you already installed are still valid.
  echo 這個角色在 gdresources_new 內沒有新圖；你之前已安裝的圖片仍然有效，不需要打包。
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
"""

INFO = {
    "MacuriUpdate": ("Macuri", "馬卡利・Λ (1289) + 夥伴 機械手臂 (498)", "Ma'curi Λ (1289) + buddy Mech Arm (498)", "Ma'curi Λ (1289) + compagnon Mech Arm (498)", """\
機械生命（裝備）：每回合受到的第一次傷害無效
槍塚：夾擊或連鎖 20%，攻擊力×1.0，連續3下
威逼（裝備）：對生命低於33%的敵人傷害×1.5（萬槍除外）
萬槍：夾擊 5%，10000傷害（不變）
夥伴 機械手臂「渴血」：每次造成傷害回復 攻擊力×0.5
""", """\
Mechanical Life (equip): the first damage taken each turn is nullified
Spear Tomb: pincer or chain 20%, 1.0x ATK, 3 hits
Coercion (equip): x1.5 damage against foes below 33% HP (Ten Thousand Spears excepted)
Ten Thousand Spears: pincer 5%, 10000 damage (unchanged)
Buddy Mech Arm 'Bloodthirst': every damaging hit heals 0.5x ATK
"""),
    "KanaUpdate": ("Kana", "卡奈・Λ (1290) + 夥伴 心動左輪 (499)", "Kana Λ (1290) + buddy Heart-Throb Revolver (499)", "Kana Λ (1290) + compagnon Heart-Throb Revolver (499)", """\
心跳加速：不變（移動她所在的夥伴得到一回合全能力提升）
病毒子彈：夾擊或連鎖 40%，中毒（2.0），毒發時卡奈回血
反差萌（裝備）：受到魔法傷害時傷害歸零並讓對方染上粉毒；物理不處理；已移除50%迴避
女王蜂：夾擊或連鎖 10%，只對敵人施加粉毒
夥伴 心動左輪「心動病毒」：直線夾擊；敵人技能/攻擊發動機率 −50%（3回合）
""", """\
Heartbeat: unchanged (an ally moved with her gets a 1-turn all-stats boost)
Virus Bullet: pincer or chain 40%, poison (2.0), each tick heals Kana
Contrast (equip): magic damage against her becomes 0 and leaves the attacker with Pink Heart Poison; physical untouched; the 50% evade is gone
Queen Bee: pincer or chain 10%, Pink Heart Poison on enemies only
Buddy Heart-Throb Revolver 'Heart-Throb Virus': pincer line; foe skill/attack rate -50% (3 turns)
"""),
    "GugbaUpdate": ("Gugba", "格古巴・Λ (1291) + 夥伴 月魂 (500)", "Gugba Λ (1291) + buddy Moon Soul (500)", "Gugba Λ (1291) + compagnon Moon Soul (500)", """\
別擋路：不變
威士忌：夾擊 30%，每杯隨機一項能力+25%（每項最多4杯，共16杯），受到任何傷害全部歸零重算
地震斬：夾擊 30%，橫3列，攻擊力×3.0＋重力（可被抵抗）
格古巴大地震：夾擊或連鎖 5%，全體敵人×1.0 連5下，隨機3種異常，洗牌位置
夥伴 月魂「奶奶的意志」：點擊，每場一次；敵人防禦−99%，下一次夾擊變重拳（倍率=被打次數，上限20）；被打滿20次說「夠了…」
""", """\
Out of the Way: unchanged
Whiskey: pincer 30%, each drink +25% to a random stat (4 per stat, 16 in all); any damage taken resets everything
Quake Slash: pincer 30%, 3 rows, 3.0x ATK + gravity (resistible)
Gugba's Great Quake: pincer or chain 5%, all enemies x1.0 five times, 3 random ailments, positions shuffled
Buddy Moon Soul 'Grandma's Will': tap, once per battle; foes' DEF -99%, the next pincer becomes a fist (multiplier = times hit, max 20); says 'Enough...' at 20 hits
"""),
    "YapkarUpdate": ("Yapkar", "亞普卡?・Λ (1292)", "Y'apkar? Λ (1292)", "Y'apkar? Λ (1292)", """\
妄想：不變
瘋狂：夾擊或連鎖 50%，火/冰/暗/雷各×0.5（共用一次判定）；共生的亞普卡(557) 防禦與魔防 +100%
覺醒：夾擊或連鎖 30%，太陽/月亮/重力/閃光各×1.0（共用一次判定）；共生的亞普卡 攻擊與魔攻 +100%
光環：全場復活一次（1/2血）；有亞普卡時亞普卡可無限復活（1/2血）
""", """\
Delusion: unchanged
Madness: pincer or chain 50%, fire/ice/dark/thunder x0.5 each (one shared roll); a symbiotic Y'apkar (557) gets DEF and MDEF +100%
Awakening: pincer or chain 30%, sun/moon/gravity/photon x1.0 each (one shared roll); a symbiotic Y'apkar gets ATK and MATK +100%
Aura: revives the whole field once (1/2 HP); with Y'apkar present she revives endlessly (1/2 HP)
"""),
}

def readme(folder):
    short, zh, en, fr, szh, sen = INFO[folder]
    return f"""================ 繁體中文 ================
{folder}：{zh}
這個資料夾只包含這一個角色的所有東西（技能資料、原生補丁、圖示、圖片），可單獨打包成自己的 APK，也可以和別的 Update 資料夾組合進同一個 APK（見上層 組合說明）。

技能：
{szh}
自己打包：先看上層 Kit\\BUILD 說明；基本上只要雙擊「build.bat」（需要 WSL；請保持 TerraModUpdate 整個資料夾完整，不要只複製這一個資料夾）。
成品：out\\TerraBattle-mod.apk、out\\reTB-Host-mod.apk、out\\SHA256.txt（遊戲 APK 簽名與以前相同，可直接覆蓋安裝；先裝 Host 再裝遊戲）。
release\\：已經打包好的分割檔，雙擊 join_apk.bat 合併並顯示 SHA256。
圖片：make_gdresources_tar.bat 只把 gdresources_new 的新圖打成 gdresources_new.tar（不碰你的原檔）；沒有新圖的角色表示你已安裝的圖片仍然有效。
注意：原生補丁只有模擬器驗證，尚未在遊戲內實測。

================ English ================
{folder}: {en}
This folder holds everything of this one character (skill data, native patch, icons, images). It builds its own standalone APK, and can also be combined with other Update folders into one APK (see the combo notes one level up).

Skills:
{sen}
Build it yourself: double-click "build.bat" (needs WSL; keep the whole TerraModUpdate folder together, do not copy only this folder).
Results: out\\TerraBattle-mod.apk, out\\reTB-Host-mod.apk, out\\SHA256.txt (same signing key as before, installs over the old one; install the Host first, then the game).
release\\: the prebuilt split files; double-click join_apk.bat to join them and show the SHA256.
Images: make_gdresources_tar.bat packs only the new images of gdresources_new into gdresources_new.tar (your own files are untouched); a character without new images keeps the images you already installed.
Note: the native patches are emulator-verified only and have not been tested in the game yet.

================ Français ================
{folder} : {fr}
Ce dossier contient tout ce qui concerne ce personnage (données de compétences, patch natif, icônes, images). Il produit son propre APK autonome et peut aussi être combiné avec d'autres dossiers Update dans un seul APK.
Compiler : double-cliquer sur « build.bat » (WSL requis ; garder tout le dossier TerraModUpdate ensemble). Résultats dans out\\. join_apk.bat assemble les parties de release\\. make_gdresources_tar.bat emballe uniquement les nouvelles images.
Remarque : les patchs natifs ne sont vérifiés que par émulateur, pas encore testés dans le jeu.
"""

for folder in INFO:
    d = os.path.join(root, folder)
    w(os.path.join(d, "build.bat"), BUILD_BAT.replace("%NAME%", folder).replace("%FOLDERS_SET%", "").replace("%FOLDERS%", folder))
    w(os.path.join(d, "join_apk.bat"), JOIN_BAT)
    w(os.path.join(d, "make_gdresources_tar.bat"), TAR_BAT)
    w(os.path.join(d, "README.txt"), readme(folder), crlf=False)
# combo
d = os.path.join(root, "ComboUpdate")
os.makedirs(d, exist_ok=True)
w(os.path.join(d, "combo.txt"), "# One Update folder name per line (lines starting with # are ignored). Any subset works.\n# 每行一個 Update 資料夾名稱（# 開頭的行會被忽略），任意組合都可以。\nMacuriUpdate\nKanaUpdate\nGugbaUpdate\nYapkarUpdate\n")
w(os.path.join(d, "build.bat"), COMBO_BAT)
w(os.path.join(d, "join_apk.bat"), JOIN_BAT)
w(os.path.join(d, "make_gdresources_tar.bat"), TAR_BAT)
print("ok")
