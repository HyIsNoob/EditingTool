import os
import sys
import platform
import subprocess
import shutil
import urllib.request
import zipfile
import tarfile
import tempfile
import ctypes
from pathlib import Path

class FFmpegManager:
    """Manages ffmpeg binaries for the application"""
    
    def __init__(self):
        self.app_dir = self._get_app_dir()
        # Location where bundled ffmpeg will be stored/extracted
        self.bin_dir = os.path.join(self.app_dir, "bin")
        
        # Create bin directory if it doesn't exist
        os.makedirs(self.bin_dir, exist_ok=True)
        
        # Platform-specific binary names
        self.is_windows = platform.system() == "Windows"
        self.ffmpeg_exe = "ffmpeg.exe" if self.is_windows else "ffmpeg"
        self.ffprobe_exe = "ffprobe.exe" if self.is_windows else "ffprobe"
        
        # Set paths to bundled binaries
        self.ffmpeg_path = os.path.join(self.bin_dir, self.ffmpeg_exe)
        self.ffprobe_path = os.path.join(self.bin_dir, self.ffprobe_exe)
        
        # Add bin directory to PATH if binaries exist
        if self._check_bundled_binaries():
            os.environ["PATH"] = self.bin_dir + os.pathsep + os.environ["PATH"]
            # Explicitly set for yt-dlp
            if hasattr(sys, 'frozen'):  # Check if we're running in a PyInstaller bundle
                # For packaged apps, set the global environment variable for yt-dlp
                os.environ["FFMPEG_LOCATION"] = self.ffmpeg_path

        # Add a compatibility layer for yt-dlp
        self._add_compatibility_layer()
    
    def _add_compatibility_layer(self):
        """Add compatibility layer for yt-dlp"""
        try:
            import yt_dlp.utils
            
            # Check if the get_exe_dir function doesn't exist
            if not hasattr(yt_dlp.utils, 'get_exe_dir'):
                # Add a simple implementation of get_exe_dir
                def get_exe_dir():
                    if hasattr(sys, 'frozen'):
                        return os.path.dirname(sys.executable)
                    else:
                        return os.path.dirname(os.path.abspath(sys.argv[0]))
                
                # Monkey patch the function into yt_dlp.utils
                yt_dlp.utils.get_exe_dir = get_exe_dir
                
                print("Added compatibility layer for yt-dlp")
        except ImportError:
            # yt-dlp is not imported yet, no need to add compatibility
            pass
    
    def _get_app_dir(self):
        """Get the application directory"""
        if getattr(sys, 'frozen', False):
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            return os.path.dirname(sys.executable)
        else:
            # Running in normal Python environment
            return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def _check_bundled_binaries(self):
        """Check if ffmpeg binaries are bundled with the application"""
        ffmpeg_exists = os.path.exists(self.ffmpeg_path)
        ffprobe_exists = os.path.exists(self.ffprobe_path)
        return ffmpeg_exists and ffprobe_exists
    
    def check_system_ffmpeg(self):
        """Check if ffmpeg is installed on the system"""
        try:
            # Try to execute ffmpeg to see if it's in PATH
            subprocess.run(
                ["ffmpeg", "-version"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                check=True
            )
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def ensure_ffmpeg_available(self, auto_download=True):
        """Ensure ffmpeg is available, downloading if needed and permitted"""
        # First check bundled binaries
        if self._check_bundled_binaries():
            # Update system environment variables to make sure yt-dlp finds FFmpeg
            os.environ["PATH"] = self.bin_dir + os.pathsep + os.environ["PATH"]
            os.environ["FFMPEG_LOCATION"] = self.ffmpeg_path
            return True
        
        # Then check system ffmpeg
        if self.check_system_ffmpeg():
            return True
        
        # If not available and auto_download is enabled, download it
        if auto_download:
            try:
                return self.download_ffmpeg()
            except Exception as e:
                print(f"Failed to download FFmpeg: {e}")
                return False
        
        return False
    
    def download_ffmpeg(self):
        """Download and extract ffmpeg binaries appropriate for the platform"""
        system = platform.system()
        machine = platform.machine().lower()
        
        # Determine download URL based on platform
        if system == "Windows":
            if "amd64" in machine or "x86_64" in machine:
                url = "https://github.com/GyanD/codexffmpeg/releases/download/5.1.2/ffmpeg-5.1.2-essentials_build.zip"
            else:
                url = "https://github.com/GyanD/codexffmpeg/releases/download/5.1.2/ffmpeg-5.1.2-essentials_build.zip"
        elif system == "Darwin":  # macOS
            if "arm" in machine or "aarch64" in machine:  # Apple Silicon
                url = "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/5.1.2/zip"
            else:  # Intel Mac
                url = "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/5.1.2/zip"
        else:  # Linux
            if "amd64" in machine or "x86_64" in machine:
                url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
            elif "arm" in machine or "aarch64" in machine:
                url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz"
            else:
                raise Exception(f"Unsupported Linux architecture: {machine}")
        
        # Create a temporary directory for download
        temp_dir = tempfile.mkdtemp()
        try:
            # Download the file
            temp_file = os.path.join(temp_dir, "ffmpeg_download")
            urllib.request.urlretrieve(url, temp_file)
            
            # Extract based on file type
            if url.endswith(".zip"):
                with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
            elif url.endswith(".tar.xz"):
                with tarfile.open(temp_file, 'r:xz') as tar_ref:
                    tar_ref.extractall(temp_dir)
            
            # Find the ffmpeg and ffprobe executables in the extracted files
            ffmpeg_path = None
            ffprobe_path = None
            
            # Search for the executables
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    if file.lower() == self.ffmpeg_exe.lower():
                        ffmpeg_path = os.path.join(root, file)
                    elif file.lower() == self.ffprobe_exe.lower():
                        ffprobe_path = os.path.join(root, file)
            
            # Move to bin directory
            if ffmpeg_path and os.path.exists(ffmpeg_path):
                shutil.copy2(ffmpeg_path, self.ffmpeg_path)
                os.chmod(self.ffmpeg_path, 0o755)  # Ensure executable
            
            if ffprobe_path and os.path.exists(ffprobe_path):
                shutil.copy2(ffprobe_path, self.ffprobe_path)
                os.chmod(self.ffprobe_path, 0o755)  # Ensure executable
            
            return self._check_bundled_binaries()
            
        finally:
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def get_ffmpeg_path(self):
        """Get the path to the ffmpeg executable"""
        if self._check_bundled_binaries():
            return self.ffmpeg_path
        
        # Try to find ffmpeg in PATH
        ffmpeg_in_path = shutil.which("ffmpeg")
        if ffmpeg_in_path:
            return ffmpeg_in_path
        
        return None
    
    def get_ffprobe_path(self):
        """Get the path to the ffprobe executable"""
        if self._check_bundled_binaries():
            return self.ffprobe_path
        
        # Try to find ffprobe in PATH
        ffprobe_in_path = shutil.which("ffprobe")
        if ffprobe_in_path:
            return ffprobe_in_path
        
        return None
