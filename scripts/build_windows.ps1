$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
Write-Host '[1/3] Installing build dependencies...'
python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'pip upgrade failed' }
python -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
Write-Host '[2/3] Running unit tests...'
python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
Write-Host '[3/3] Packaging Windows single-file executable...'
python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name 'SRT-UTF8-Studio' `
    --icon 'assets/app.ico' `
    --add-data 'assets/app.png;assets' `
    --add-data 'assets/app.ico;assets' `
    --hidden-import 'PySide6.QtWidgets' `
    app.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
Write-Host 'Done! dist\SRT-UTF8-Studio.exe' -ForegroundColor Green
