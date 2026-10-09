@echo off
setlocal
echo =======================================================
echo  Building Antigravity Rewind Desktop App (Standalone)
echo =======================================================

cd /d "%~dp0"

pyinstaller --noconfirm --clean --onefile --windowed ^
    --name "AntigravityRewind" ^
    --icon="icon.ico" ^
    --add-data "icon.ico;." ^
    --add-data "icon.png;." ^
    --add-data "index.html;." ^
    --add-data "tailwind.js;." ^
    --add-data "lucide.js;." ^
    --add-data "marked.js;." ^
    --add-data "backend.py;." ^
    app.py

if %ERRORLEVEL% equ 0 (
    echo [SUCCESS] Binary created in dist\AntigravityRewind.exe
    copy /y "dist\AntigravityRewind.exe" "AntigravityRewind.exe"
    for %%I in ("AntigravityRewind.exe") do echo [SIZE] %%~zI bytes
) else (
    echo [FAILED] Build failed with code %ERRORLEVEL%
)

endlocal
