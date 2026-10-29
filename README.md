# SRT UTF-8 Studio

A modern Windows desktop app for converting subtitle files into **UTF-8 without a byte-order mark (BOM)**. Designed for Turkish subtitles that may have been authored in **Windows-1254** and display as Cyrillic or broken characters on certain video players.

**Developer:** [@cumaduran](https://github.com/cumaduran)  
**Platform:** Windows 10/11 (64-bit)  
**License:** MIT (application code). Qt / PySide6 has its own LGPL licensing terms.

## Features

- Modern dark-mode graphical interface powered by Qt / PySide6.
- Add an individual `.srt`, select multiple files, or import folders.
- Drag and drop subtitles or directories into the app.
- Recursive folder scanning, with an option to preserve subfolder paths.
- Save automatically into an adjacent `utf8` directory or choose any custom output folder.
- Existing **UTF-8**, **UTF-8 with BOM**, **UTF-16 with BOM**, and Turkish **Windows-1254** input support.
- Strict decoding: invalid or ambiguous content is reported instead of silently replacing characters.
- Unicode content is written in UTF-8 **without BOM** and with the original line endings intact.
- File-level progress, result statuses, and cancellation between files.
- Original subtitle files are never overwritten; existing output files are skipped by default.
- A CLI is included for scripting and automated conversion.
- GitHub Actions produces a downloadable Windows `.exe` on every push and attaches it to tagged Releases.

## Download / install

Go to this repository's **Releases** page, download `SRT-UTF8-Studio.exe` from the newest release, and run it. There is no Python installation required for the Windows EXE.

> The application is not code-signed. Windows SmartScreen may warn on a first run. Only download releases from a repository you trust, and inspect the source when in doubt.

## How to use (GUI)

1. Launch `SRT-UTF8-Studio.exe`.
2. Add `.srt` files using **Dosya seç** or folders using **Klasör seç**, or drag them into the drop area.
3. Leave **Kaynak yanında /utf8 klasörü** selected to create an output directory next to the source folder, or select **Özel çıktı klasörü** and choose a destination.
4. Choose whether to scan subfolders and preserve their directory structure.
5. Click **Dönüştürmeyi başlat**.
6. Read the file-level result statuses and open the output folder.
7. Upload the converted `.srt` files to your video host, replacing the previously attached subtitles if needed.

Example automatic output:

```text
Naruto/
└── subtitles/
    ├── ANKANRT001.srt
    ├── ANKANRT002.srt
    └── utf8/                 # created automatically
        ├── ANKANRT001.srt   # UTF-8, no BOM
        └── ANKANRT002.srt
```

**Selection details:** If several source folders are selected and a *custom output folder* is used, each source folder is given a directory named after that source folder to reduce collisions. Files explicitly selected as individuals are stored at the destination root. If two inputs would produce the same output path, the second is reported as skipped rather than overwriting the first. The app excludes existing `utf8` subdirectories during recursive scans to avoid processing prior outputs again.

**Overwrite:** Disabled by default. If enabled, existing output files may be replaced, but original input files are still kept separate.

## Encoding behavior

The app checks for a Unicode BOM, then tries strict UTF-8 decoding. If that fails, it attempts **Windows-1254** (Turkish) decoding. It never treats already-valid UTF-8 as Windows-1254. Output is always UTF-8 without BOM. Subtitle timing and line breaks are preserved; no translation or spelling changes are made.

> If your input already contains the Unicode replacement character `�` or the wrong text, conversion alone **cannot recover lost characters**. The app reports a warning for `�`. Similarly, if a file was originally authored in another legacy encoding, automatic Windows-1254 fallback may not be appropriate; check its detected source encoding.

## Run from source

Requires **Python 3.10+** and a graphical environment.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Or use `run_windows.bat` to install Python dependencies and launch the GUI.

## Build a Windows EXE locally

On a Windows PC with Python installed:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

Alternatively, double-click `build_windows.bat`. Output: `dist\SRT-UTF8-Studio.exe`. This uses **PyInstaller** (`--onefile --windowed`). Build Windows binaries on Windows: PyInstaller is not a cross-compiler.

## GitHub repository and EXE deployment

1. Create a GitHub repository named `srt-utf8-studio` (or any name you prefer).
2. Upload all project files, including the hidden `.github/workflows/` directory.
3. Run the following inside the project directory:

```powershell
git init
git add .
git commit -m "Initial release: SRT UTF-8 Studio"
git branch -M main
git remote add origin https://github.com/cumaduran/srt-utf8-studio.git
git push -u origin main
```

**Automatic build:** the **Windows EXE Build** workflow runs on push, pull request or manual dispatch. Open **Actions** → select the successful run → download **SRT-UTF8-Studio-Windows-x64**. GitHub Actions downloads are artifacts, not Releases.

**Publish a downloadable release:** tag and push a version:

```powershell
git tag v1.0.0
git push origin v1.0.0
```

The **Publish Windows Release** workflow runs tests, builds the EXE on Windows, creates a GitHub Release, and attaches `SRT-UTF8-Studio.exe` to it. The workflow uses the repository's built-in `GITHUB_TOKEN` with `contents: write` permissions. The repository must allow GitHub Actions; check **Settings → Actions** if the workflow is disabled.

> No EXE is included in this source archive: Windows CI or a Windows local build must generate the final executable. A workflow is not itself proof that the EXE was built successfully; check the Actions run result.

## CLI usage

The conversion engine also runs without Qt:

```powershell
python -m srtstudio.cli "C:\Videos\naruto\0srt"
python -m srtstudio.cli "C:\My Subs" -o "D:\Processed Subs"
python -m srtstudio.cli episode01.srt episode02.srt --overwrite
```

Useful switches: `--flat`, `--no-recursive`, `--overwrite`.

## Testing

```powershell
python -m unittest discover -s tests -v
```

Tests cover Turkish Windows-1254 conversions, UTF-8 BOM removal, existing UTF-8, UTF-16, newline preservation, multi-file output, destination collisions, recursion, cancellation, and safety checks.

## Attribution and dependencies

Application developed by [cumaduran](https://github.com/cumaduran). GUI framework: [Qt for Python / PySide6](https://doc.qt.io/qtforpython-6/) (LGPLv3 / commercial licensing options). Before distributing EXE builds, review the Qt licensing and notice requirements for bundled dynamic Qt libraries. This project's MIT license only covers original application code and assets.
