import PyInstaller.__main__
import os
import sys
import shutil
import subprocess
import platform

def get_ffmpeg_binaries():
    """Ensure FFmpeg binaries are included in the package"""
    print("Checking for FFmpeg...")
    
    bin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")
    os.makedirs(bin_dir, exist_ok=True)
    
    # Ensure FFmpeg is available
    from utils.compat import ensure_ffmpeg_available
    ffmpeg_available, ffmpeg_path = ensure_ffmpeg_available()
    
    ffmpeg_exe = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    ffmpeg_dest = os.path.join(bin_dir, ffmpeg_exe)
    
    # Copy FFmpeg to bin directory if not already there
    if ffmpeg_available and ffmpeg_path:
        if not os.path.exists(ffmpeg_dest) and os.path.exists(ffmpeg_path):
            print(f"Copying FFmpeg from {ffmpeg_path} to {ffmpeg_dest}")
            shutil.copy2(ffmpeg_path, ffmpeg_dest)
    else:
        print("Warning: FFmpeg binaries not included. The packaged app may have limited functionality.")

def create_package():
    """Create the packaged application using PyInstaller"""
    print("Starting application packaging...")
    
    # Set output directory to drive D
    output_dir = "D:\\KHyTool_Build"
    os.makedirs(output_dir, exist_ok=True)
    
    # Clean previous builds
    for directory in [os.path.join(output_dir, 'dist'), os.path.join(output_dir, 'build')]:
        if os.path.exists(directory):
            print(f"Removing existing {directory} directory")
            shutil.rmtree(directory)
    
    # PyInstaller options with drive D as the output directory
    pyinstaller_options = [
        'main.py',
        '--name=KHyTool',
        '--onefile',
        '--windowed',
        '--distpath=' + os.path.join(output_dir, 'dist'),
        '--workpath=' + os.path.join(output_dir, 'build'),
        '--specpath=' + output_dir,
        '--icon=resources/icons/app_icon.ico' if os.path.exists('resources/icons/app_icon.ico') else None,
        f'--add-data=bin{os.pathsep}bin',  # Include bin directory with FFmpeg
        '--clean',
    ]
    
    # Run PyInstaller
    print("Running PyInstaller...")
    PyInstaller.__main__.run(pyinstaller_options)
    
    print("\nPackaging complete!")
    print(f"The packaged application is available at: {os.path.join(output_dir, 'dist', 'KHyTool')}")

if __name__ == "__main__":
    print("KHyTool Packaging Utility")
    print("=========================")
    
    # Ensure FFmpeg binaries are included
    get_ffmpeg_binaries()
    
    # Create the package
    create_package()
