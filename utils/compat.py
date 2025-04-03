"""
Compatibility utilities for ensuring consistent behavior across environments,
especially in packaged applications.
"""
import os
import sys
import logging
import shutil
import subprocess
from pathlib import Path

# Set up logging
logger = logging.getLogger(__name__)

def setup_yt_dlp_compatibility():
    """
    Add necessary compatibility fixes for yt-dlp module.
    This is especially needed when the application is packaged.
    """
    try:
        import yt_dlp.utils
        
        # Add get_exe_dir function if it doesn't exist
        if not hasattr(yt_dlp.utils, 'get_exe_dir'):
            def get_exe_dir():
                """Return directory containing executable and bundled dependencies."""
                if hasattr(sys, 'frozen'):
                    return os.path.dirname(sys.executable)
                else:
                    return os.path.dirname(os.path.abspath(sys.argv[0]))
            
            # Add function to module
            yt_dlp.utils.get_exe_dir = get_exe_dir
            logger.info("Added yt-dlp compatibility layer: get_exe_dir function")
        
        # Ensure other compatibility fixes as needed
        return True
    except ImportError:
        logger.warning("yt-dlp not installed, compatibility layer not applied")
        return False

def ensure_ffmpeg_available():
    """
    Ensure FFmpeg is available either in PATH, app directory or bundled with the app.
    Returns a tuple (success, ffmpeg_path)
    """
    ffmpeg_executable = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    
    # Check for FFmpeg in different locations
    ffmpeg_paths = []
    
    # 1. Check PATH
    if shutil.which(ffmpeg_executable):
        ffmpeg_paths.append(shutil.which(ffmpeg_executable))
    
    # 2. Check application root directory (for packaged app)
    if hasattr(sys, 'frozen'):
        app_dir = os.path.dirname(sys.executable)
        ffmpeg_in_app = os.path.join(app_dir, ffmpeg_executable)
        if os.path.exists(ffmpeg_in_app):
            ffmpeg_paths.append(ffmpeg_in_app)
    
    # 3. Check bin directory
    bin_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin")
    ffmpeg_in_bin = os.path.join(bin_dir, ffmpeg_executable)
    if os.path.exists(ffmpeg_in_bin):
        ffmpeg_paths.append(ffmpeg_in_bin)
    
    # 4. Check current working directory
    ffmpeg_in_cwd = os.path.join(os.getcwd(), ffmpeg_executable)
    if os.path.exists(ffmpeg_in_cwd):
        ffmpeg_paths.append(ffmpeg_in_cwd)
    
    # If FFmpeg is found, set up environment
    if ffmpeg_paths:
        ffmpeg_path = ffmpeg_paths[0]
        
        # Set FFmpeg location in environment variable
        os.environ["FFMPEG_LOCATION"] = ffmpeg_path
        
        # In packaged app, also add the directory to PATH
        if hasattr(sys, 'frozen'):
            ffmpeg_dir = os.path.dirname(ffmpeg_path)
            if ffmpeg_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
        
        logger.info(f"FFmpeg found at: {ffmpeg_path}")
        return True, ffmpeg_path
    else:
        logger.warning("FFmpeg not found in any location")
        return False, None

def verify_ffmpeg_working():
    """
    Verify that FFmpeg is working properly by running a simple command.
    Returns True if FFmpeg is working, False otherwise.
    """
    try:
        # Try running ffmpeg -version
        subprocess.run(
            ["ffmpeg", "-version"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            timeout=5
        )
        return True
    except Exception as e:
        logger.error(f"FFmpeg verification failed: {str(e)}")
        return False

# Initialize compatibility fixes
def init_compatibility():
    """Initialize all compatibility fixes"""
    setup_yt_dlp_compatibility()
    ffmpeg_available, ffmpeg_path = ensure_ffmpeg_available()
    
    if ffmpeg_available and verify_ffmpeg_working():
        logger.info("Compatibility layer initialized successfully")
        return True
    else:
        logger.warning("Compatibility layer initialization incomplete")
        return False

# Run initialization when module is imported
init_result = init_compatibility()
