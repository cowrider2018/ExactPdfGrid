@echo off
chcp 65001 > nul
cd /d "%~dp0"

:: 1. Create virtual environment if missing
if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment. Make sure Python is installed and on PATH.
        pause
        exit /b 1
    )
) else (
    echo [1/4] Virtual environment already exists, skipping creation
)

:: 2. Editable install with web UI + both OCR runtimes.
::    [web]      -> Flask server / Web UI
::    [ocr-all]  -> unified rapidocr + OpenVINO + ONNX Runtime, so every
::                  engine option in the UI (pymupdf / rapidocr /
::                  rapidocr-vino / rapidocr-onnx) works out of the box.
::    OpenVINO is the heavier download; the first run may take a while.
echo [2/4] Installing exactpdfgrid (editable, with [web,ocr-all] extras)...
.venv\Scripts\python.exe -m pip install -e ".[web,ocr-all]" --quiet
if errorlevel 1 (
    echo ERROR: Installation failed
    pause
    exit /b 1
)
echo Installed exactpdfgrid in editable mode (web + OpenVINO/ONNX OCR)

:: 3. Create output folder if missing
if not exist "output" mkdir output

:: 4. Start server in the same window
echo [3/4] Starting server...
start "" /B .venv\Scripts\exactpdfgrid-web.exe

:: 5. Open browser
echo [4/4] Opening browser
timeout /t 2 /nobreak > nul
start "" "http://localhost:5000"

echo.
echo Server is running at http://localhost:5000
echo To stop the server, close this command window
pause
