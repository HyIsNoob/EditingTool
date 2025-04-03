"""
Runtime environment checks for KHyTool
Used to validate the environment at application startup
"""
import os
import sys
import platform
import subprocess
import logging
import shutil
from pathlib import Path
from PyQt5.QtWidgets import QMessageBox

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('khytool_runtime.log')
    ]
)
logger = logging.getLogger('KHyTool')

def get_app_root():
    """Get application root directory"""
    if getattr(sys, 'frozen', False):
        # Running as packaged app
        return os.path.dirname(sys.executable)
    else:
        # Running from source
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def check_ffmpeg():
    """Check if FFmpeg is available"""
    logger.info("Checking FFmpeg availability...")
    
    ffmpeg_executable = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    ffmpeg_paths = []
    
    # 1. Check bin directory (relative to app root)
    bin_dir = os.path.join(get_app_root(), "bin")
    ffmpeg_in_bin = os.path.join(bin_dir, ffmpeg_executable)
    if os.path.exists(ffmpeg_in_bin):
        ffmpeg_paths.append(ffmpeg_in_bin)
        logger.info(f"FFmpeg found in bin directory: {ffmpeg_in_bin}")
    
    # 2. Check app root directory
    ffmpeg_in_root = os.path.join(get_app_root(), ffmpeg_executable)
    if os.path.exists(ffmpeg_in_root):
        ffmpeg_paths.append(ffmpeg_in_root)
        logger.info(f"FFmpeg found in app root: {ffmpeg_in_root}")
    
    # 3. Check PATH
    ffmpeg_in_path = shutil.which(ffmpeg_executable)
    if ffmpeg_in_path:
        ffmpeg_paths.append(ffmpeg_in_path)
        logger.info(f"FFmpeg found in PATH: {ffmpeg_in_path}")
    
    if not ffmpeg_paths:
        logger.warning("FFmpeg not found in any location")
        return False, None
    
    # Test that FFmpeg actually works
    ffmpeg_path = ffmpeg_paths[0]
    try:
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )
        if result.returncode == 0:
            version_info = result.stdout.decode('utf-8', errors='ignore').split('\n')[0]
            logger.info(f"FFmpeg is working: {version_info}")
            return True, ffmpeg_path
        else:
            logger.error(f"FFmpeg returned error code: {result.returncode}")
            return False, ffmpeg_path
    except Exception as e:
        logger.error(f"Error running FFmpeg: {str(e)}")
        return False, ffmpeg_path

def check_environment():
    """Run all environment checks"""
    logger.info(f"Performing environment checks for KHyTool...")
    logger.info(f"Platform: {platform.platform()}")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Executable: {sys.executable}")
    logger.info(f"App root: {get_app_root()}")
    
    # Check if running as packaged app
    if getattr(sys, 'frozen', False):
        logger.info("Running as packaged application")
    else:
        logger.info("Running from source")
    
    # Check FFmpeg
    ffmpeg_ok, ffmpeg_path = check_ffmpeg()
    
    # Set environment variables if needed
    if ffmpeg_ok and ffmpeg_path:
        os.environ["FFMPEG_LOCATION"] = ffmpeg_path
        # Add to PATH if not already there
        ffmpeg_dir = os.path.dirname(ffmpeg_path)
        if ffmpeg_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ["PATH"]
        logger.info(f"Set FFMPEG_LOCATION to {ffmpeg_path}")
    
    # Return overall status
    return {
        "ffmpeg": {
            "available": ffmpeg_ok,
            "path": ffmpeg_path
        },
        "is_packaged": getattr(sys, 'frozen', False),
        "system": platform.system(),
        "python_version": platform.python_version()
    }

if __name__ == "__main__":
    # Run checks when script is executed directly
    status = check_environment()
    print("\nEnvironment Check Results:")
    print(f"FFmpeg Available: {'✓' if status['ffmpeg']['available'] else '✗'}")
    if status['ffmpeg']['path']:
        print(f"FFmpeg Path: {status['ffmpeg']['path']}")
    print(f"Running as packaged app: {'✓' if status['is_packaged'] else '✗'}")
    print(f"System: {status['system']}")
    print(f"Python Version: {status['python_version']}")
