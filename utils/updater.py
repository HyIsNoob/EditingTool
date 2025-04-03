import os
import sys
import json
import tempfile
import shutil
import subprocess
import platform
import time
import zipfile
import requests
from PyQt5.QtCore import QObject, pyqtSignal

class Updater(QObject):
    """Class to handle application updates from GitHub"""
    
    update_available = pyqtSignal(str, str)  # new_version, release_notes
    update_progress = pyqtSignal(int, str)  # percentage, status
    update_completed = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, github_repo, current_version, app_dir=None):
        """Initialize the updater
        
        Args:
            github_repo (str): GitHub repository in format "username/repo"
            current_version (str): Current application version
            app_dir (str, optional): Application directory. Defaults to directory of main script.
        """
        super().__init__()
        self.github_repo = github_repo
        self.current_version = current_version
        
        if app_dir is None:
            self.app_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            self.app_dir = app_dir
            
        self.api_url = f"https://api.github.com/repos/{github_repo}/releases/latest"
        self.download_url = None
        self.new_version = None
        self.release_notes = None
    
    def check_for_updates(self):
        """Check if updates are available
        
        Returns:
            bool: True if update available, False otherwise
        """
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()  # Raise exception for 4XX/5XX status codes
            
            release_data = response.json()
            self.new_version = release_data['tag_name'].lstrip('v')  # Remove 'v' prefix if present
            self.release_notes = release_data['body']
            
            # Find asset URL
            for asset in release_data['assets']:
                if asset['name'].endswith('.zip'):
                    self.download_url = asset['browser_download_url']
                    break
            
            # Compare versions
            if self._version_is_newer(self.new_version, self.current_version):
                self.update_available.emit(self.new_version, self.release_notes)
                return True
            return False
        
        except Exception as e:
            print(f"Error checking for updates: {str(e)}")
            return False
    
    def download_and_install_update(self):
        """Download and install the update"""
        if not self.download_url:
            self.update_completed.emit(False, "No download URL available")
            return False
        
        try:
            # Create temp directory
            temp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(temp_dir, "update.zip")
            
            # Download update file
            self.update_progress.emit(10, "Đang tải bản cập nhật...")
            response = requests.get(self.download_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192
            downloaded = 0
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(block_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = int(30 * downloaded / total_size) + 10
                            self.update_progress.emit(progress, f"Đang tải: {downloaded//1024}/{total_size//1024} KB")
            
            # Extract update
            self.update_progress.emit(40, "Đang giải nén...")
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Prepare for update installation
            self.update_progress.emit(60, "Đang cài đặt bản cập nhật...")
            
            # Windows: Create a batch file to complete the update
            if platform.system() == "Windows":
                self._create_windows_updater(extract_dir, temp_dir)
            else:
                self._create_unix_updater(extract_dir, temp_dir)
                
            self.update_progress.emit(100, "Cập nhật hoàn tất. Ứng dụng sẽ khởi động lại.")
            self.update_completed.emit(True, "Đã tải bản cập nhật thành công. Ứng dụng sẽ khởi động lại để áp dụng thay đổi.")
            
            # Wait a moment for signals to be processed
            time.sleep(1)
            
            # Start the updater process
            if platform.system() == "Windows":
                subprocess.Popen([os.path.join(temp_dir, "update.bat")], 
                                 creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            else:
                subprocess.Popen(['/bin/bash', os.path.join(temp_dir, "update.sh")])
                
            # Exit app to let the updater take over
            sys.exit(0)
            
        except Exception as e:
            self.update_completed.emit(False, f"Cập nhật thất bại: {str(e)}")
            return False
    
    def _version_is_newer(self, new_version, current_version):
        """Compare versions to determine if new_version is newer"""
        try:
            new_parts = [int(x) for x in new_version.split('.')]
            current_parts = [int(x) for x in current_version.split('.')]
            
            # Pad with zeros if needed
            while len(new_parts) < len(current_parts):
                new_parts.append(0)
            while len(current_parts) < len(new_parts):
                current_parts.append(0)
                
            # Compare each segment
            for new, current in zip(new_parts, current_parts):
                if new > current:
                    return True
                if new < current:
                    return False
            
            # All segments are equal
            return False
            
        except ValueError:
            # Fallback to simple string comparison if parsing fails
            return new_version > current_version
    
    def _create_windows_updater(self, extract_dir, temp_dir):
        """Create Windows batch file for update installation"""
        batch_path = os.path.join(temp_dir, "update.bat")
        
        with open(batch_path, 'w') as f:
            f.write('@echo off\n')
            f.write('echo Đang áp dụng bản cập nhật, vui lòng chờ...\n')
            f.write('timeout /t 2 /nobreak >nul\n')  # Wait for app to exit
            
            # Copy new files to app directory
            f.write(f'xcopy /E /Y /I "{extract_dir}\\*.*" "{self.app_dir}"\n')
            
            # Clean up temp directory
            f.write(f'rmdir /S /Q "{temp_dir}"\n')
            
            # Restart the application
            f.write(f'start "" "{self.app_dir}\\KHyTool.exe"\n')
            f.write('exit\n')
    
    def _create_unix_updater(self, extract_dir, temp_dir):
        """Create Unix shell script for update installation"""
        shell_path = os.path.join(temp_dir, "update.sh")
        
        with open(shell_path, 'w') as f:
            f.write('#!/bin/bash\n')
            f.write('echo "Đang áp dụng bản cập nhật, vui lòng chờ..."\n')
            f.write('sleep 2\n')  # Wait for app to exit
            
            # Copy new files to app directory
            f.write(f'cp -R "{extract_dir}/"* "{self.app_dir}/"\n')
            
            # Make sure executable permissions are set
            f.write(f'chmod +x "{self.app_dir}/KHyTool"\n')
            
            # Clean up temp directory
            f.write(f'rm -rf "{temp_dir}"\n')
            
            # Restart the application
            f.write(f'"{self.app_dir}/KHyTool" &\n')
            
        # Make the script executable
        os.chmod(shell_path, 0o755)
