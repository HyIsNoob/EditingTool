@echo off
echo Building KHyTool Application...

REM Ensure Python is installed and in path
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Python is not found in PATH. Please install Python and add it to your PATH.
    exit /b 1
)

REM Install or update required packages
echo Installing required packages...
python -m pip install --upgrade pip
python -m pip install pyinstaller requests pillow pyqt5 opencv-python-headless pytesseract pydub ffmpeg-python spacy python-ffmpeg-video-streaming yt-dlp

REM Install dependencies specific to the downloaders
echo Installing multimedia and downloader dependencies...
python -m pip install youtube-dl requests urllib3 certifi chardet idna

REM Create temporary directory for build
if not exist "build" mkdir build
if not exist "dist" mkdir dist

REM Create thumbnails directory that will be included in the package
if not exist "thumbnails" mkdir thumbnails

REM Run PyInstaller with appropriate settings for our app
echo Running PyInstaller...
pyinstaller --noconfirm --clean ^
    --name KHyTool ^
    --add-data "ui;ui" ^
    --add-data "utils;utils" ^
    --add-data "config;config" ^
    --add-data "project;project" ^
    --add-data "resources;resources" ^
    --add-data "thumbnails;thumbnails" ^
    --hidden-import=cv2 ^
    --hidden-import=pytesseract ^
    --hidden-import=pydub ^
    --hidden-import=ffmpeg ^
    --hidden-import=spacy ^
    --hidden-import=yt_dlp ^
    --hidden-import=utils.download_manager ^
    --hidden-import=utils.helpers ^
    --hidden-import=utils.compat ^
    --icon=resources/icon.ico ^
    --uac-admin ^
    main.py

REM Enhance the package with additional components
echo Enhancing package with additional components...
python enhanced_package.py

REM Create the installer
echo Creating installer...
python create_installer.py

echo Build process completed. Check the 'dist' folder for the application.
pause