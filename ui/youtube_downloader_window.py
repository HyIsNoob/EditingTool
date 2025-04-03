from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFileDialog, QProgressBar, QStatusBar, QComboBox,
                             QMessageBox, QGroupBox, QFrame)
from PyQt5.QtGui import QPixmap, QFont, QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer, QSize
import os
import time
import urllib.parse
import requests
import sys
import subprocess
from io import BytesIO
from utils.helpers import clean_filename, format_size, format_time
import yt_dlp
from utils.download_manager import DownloadManager

class DownloadThread(QThread):
    progress_signal = pyqtSignal(int, str, str, str, str)  # progress, speed, downloaded, remaining_time, total_size
    finished_signal = pyqtSignal(str)  # output file
    error_signal = pyqtSignal(str)  # error message
    file_exists_signal = pyqtSignal(str)  # signal for existing file
    
    def __init__(self, url, format_id, output_path):
        super().__init__()
        self.url = url
        self.format_id = format_id
        self.output_path = output_path
        self.is_cancelled = False
        self.download_manager = DownloadManager.get_instance()
        self.download_id = None

    def run(self):
        try:
            # Thiết lập các thông tin cơ bản và tạo download_id
            self.download_id = self.download_manager.add_download(
                source='youtube',
                title=self.url,  # Ban đầu chỉ có URL, sau khi lấy thông tin sẽ cập nhật title
                thumbnail_path=None
            )
            
            # Clean the URL (remove tracking parameters)
            parsed_url = urllib.parse.urlparse(self.url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            clean_url = self.url
            
            # Set up parameters for youtube-dl
            ydl_opts = {
                'format': self.format_id,
                'outtmpl': os.path.join(self.output_path, '%(title)s_%(resolution)s.%(ext)s'),
                'noplaylist': True,
                'progress_hooks': [self.progress_hook],
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': False,
                'merge_output_format': 'mp4',  # Always merge to mp4 format
                # Explicitly specify FFmpeg options to ensure audio is included
                'postprocessor_args': {
                    'ffmpeg': ['-c:v', 'copy', '-c:a', 'aac', '-strict', 'experimental']
                }
            }
            
            # If downloading audio only
            if self.format_id == 'bestaudio':
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '320',
                    }],
                    'outtmpl': os.path.join(self.output_path, '%(title)s_Audio.%(ext)s')
                })
            # If downloading best quality, ensure we get both video and audio
            elif self.format_id == 'best':
                # More explicit format specification to ensure audio inclusion
                ydl_opts.update({
                    'format': 'bestvideo+bestaudio/best',
                    'merge_output_format': 'mp4',
                })
            # For specific format IDs, make sure we also get audio
            else:
                # More detailed format specification for specific formats
                ydl_opts.update({
                    'format': f'{self.format_id}+bestaudio/best', 
                    'merge_output_format': 'mp4',
                })
            
            # Custom logger to capture filenames
            class MyLogger:
                def __init__(self):
                    self.downloaded_files = []
                    self.last_messages = []
                
                def debug(self, msg):
                    # Strip ANSI color codes before processing
                    clean_msg = self.strip_ansi_codes(msg)
                    
                    # Store most recent messages for error diagnosis
                    self.last_messages.append(clean_msg)
                    if len(self.last_messages) > 10:
                        self.last_messages.pop(0)
                        
                    # Capture the destination filename
                    if 'Destination:' in clean_msg:
                        try:
                            filename = clean_msg.split('Destination: ')[1].strip()
                            self.downloaded_files.append(filename)
                            print(f"Debug: Found file path: {filename}")
                            
                            # Cập nhật output file trong download manager
                            self.download_manager.update_download(
                                self.download_id, 
                                output_file=filename
                            )
                        except Exception as e:
                            print(f"Error capturing filename: {str(e)}")
                    
                    # Also detect merged output files
                    elif "Merging formats into" in clean_msg:
                        try:
                            # Extract filename between quotes
                            import re
                            match = re.search(r'Merging formats into\s+"([^"]+)"', clean_msg)
                            if match:
                                filename = match.group(1)
                                self.downloaded_files.append(filename)
                                print(f"Debug: Found merged file path: {filename}")
                                
                                # Update output file in download manager
                                self.download_manager.update_download(
                                    self.download_id, 
                                    output_file=filename
                                )
                        except Exception as e:
                            print(f"Error capturing merged filename: {str(e)}")
                
                def strip_ansi_codes(self, text):
                    """Remove ANSI color codes from text"""
                    import re
                    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                    return ansi_escape.sub('', text)
                
                def warning(self, msg):
                    clean_msg = self.strip_ansi_codes(msg)
                    print(f"Warning: {clean_msg}")
                    self.last_messages.append(f"WARNING: {clean_msg}")
                    if len(self.last_messages) > 10:
                        self.last_messages.pop(0)
                
                def error(self, msg):
                    clean_msg = self.strip_ansi_codes(msg)
                    print(f"Error: {clean_msg}")
                    self.last_messages.append(f"ERROR: {clean_msg}")
                    if len(self.last_messages) > 10:
                        self.last_messages.pop(0)
            
            logger = MyLogger()
            logger.download_manager = self.download_manager
            logger.download_id = self.download_id
            ydl_opts['logger'] = logger
            
            # Additional download options to increase reliability
            ydl_opts.update({
                'retries': 10,                  # Retry up to 10 times
                'fragment_retries': 10,         # Retry fragment downloads
                'continuedl': True,             # Continue partial downloads
                'external_downloader_args': [   # Additional aria2 args for more reliability
                    '--retry-wait=2',
                    '--max-connection-per-server=16',
                    '--min-split-size=1M'
                ]
            })
            
            # Try to get info about the video first to help locate the file later if needed
            try:
                with yt_dlp.YoutubeDL({**ydl_opts, 'skip_download': True}) as ydl:
                    info_dict = ydl.extract_info(clean_url, download=False)
                    if 'title' in info_dict:
                        # Set attributes for download manager
                        download_info = self.download_manager.downloads[self.download_id]
                        download_info.title = info_dict['title']
                        
                        # Check for existing files more thoroughly BEFORE attempting download
                        existing_file = self.check_for_existing_file(info_dict['title'])
                        if existing_file:
                            self.file_exists_signal.emit(existing_file)
                            return
                        
                        # Try to save thumbnail if available in app directory
                        if 'thumbnail' in info_dict:
                            try:
                                thumbnail_url = info_dict['thumbnail']
                                # Get the application's directory
                                app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
                                # Create thumbnails directory if it doesn't exist
                                thumbnails_dir = os.path.join(app_dir, "thumbnails")
                                os.makedirs(thumbnails_dir, exist_ok=True)
                                
                                thumbnail_path = os.path.join(thumbnails_dir, f"yt_{info_dict['id']}_thumbnail.jpg")
                                
                                response = requests.get(thumbnail_url)
                                if response.status_code == 200:
                                    with open(thumbnail_path, 'wb') as f:
                                        f.write(response.content)
                                    download_info.thumbnail_path = thumbnail_path
                            except Exception as e:
                                print(f"Could not save thumbnail: {str(e)}")
            except Exception as e:
                print(f"Warning: Could not get video info: {str(e)}")
                info_dict = {'title': 'video', 'ext': 'mp4'}
            
            # Check if a file with similar name already exists
            self.handle_existing_files(info_dict.get('title', 'video'))
                
            # Now download the video
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([clean_url])
            except Exception as e:
                if "already exists" in str(e):
                    self.error_signal.emit(f"File already exists. Please delete the existing file or change the output directory.")
                    return
                elif any(err in str(e) for err in ["Unable to rename file", "process cannot access the file", "Permission denied"]):
                    # Wait for file to be released
                    self.progress_signal.emit(95, "-- KB/s", "Finalizing...", "Waiting for file access", "")
                    time.sleep(3)  # Wait for file access
                    try:
                        # Try one more time
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([clean_url])
                    except Exception as retry_err:
                        # If still fails, check if any files were downloaded
                        if not logger.downloaded_files:
                            raise retry_err
                else:
                    # If not a file access error, re-raise
                    raise e
            
            # Check if download was completed successfully
            if not self.is_cancelled:
                # Check for successful download
                if logger.downloaded_files:
                    # Get a list of all downloaded files
                    final_files = []
                    for file_path in logger.downloaded_files:
                        if os.path.exists(file_path):
                            # Check if the file has content
                            try:
                                file_size = os.path.getsize(file_path)
                                if file_size > 0:
                                    final_files.append(file_path)
                            except (OSError, IOError):
                                pass
                    
                    # If we have at least one valid file, consider download successful
                    if final_files:
                        # Use the last (most likely merged) file
                        downloaded_file = final_files[-1]
                        
                        self.download_manager.update_download(
                            self.download_id,
                            status='completed',
                            progress=100,
                            output_file=downloaded_file
                        )
                        
                        # Set the current timestamp for the downloaded file
                        self.set_current_timestamp(downloaded_file)
                        self.finished_signal.emit(downloaded_file)
                    else:
                        # Search for merged file in log messages
                        merged_file = None
                        for msg in logger.last_messages:
                            if "Merging formats into" in msg:
                                import re
                                match = re.search(r'Merging formats into\s+"([^"]+)"', msg)
                                if match:
                                    merged_file = match.group(1)
                                    if os.path.exists(merged_file) and os.path.getsize(merged_file) > 0:
                                        final_files = [merged_file]
                                        downloaded_file = merged_file
                                        
                                        self.download_manager.update_download(
                                            self.download_id,
                                            status='completed',
                                            progress=100,
                                            output_file=downloaded_file
                                        )
                                        
                                        # Set the current timestamp for the downloaded file
                                        self.set_current_timestamp(downloaded_file)
                                        self.finished_signal.emit(downloaded_file)
                                        break
                        
                        if not merged_file:
                            # We have filenames but they're not valid
                            log_info = '\n'.join(logger.last_messages[-5:])
                            
                            # Last resort: find recently created files in the output directory
                            downloaded_file = self.find_downloaded_file(info_dict.get('title', 'video'), 
                                                                    'mp3' if self.format_id == 'bestaudio' else 'mp4')
                            
                            if downloaded_file:
                                self.download_manager.update_download(
                                    self.download_id,
                                    status='completed',
                                    progress=100,
                                    output_file=downloaded_file
                                )
                                
                                # Set the current timestamp for the downloaded file
                                self.set_current_timestamp(downloaded_file)
                                self.finished_signal.emit(downloaded_file)
                            else:
                                raise Exception(f"Files were downloaded but cannot be verified. Last log messages:\n{log_info}")
                else:
                    # No files were logged - try to find the downloaded file
                    video_title = info_dict.get('title', 'video')
                    video_ext = 'mp3' if self.format_id == 'bestaudio' else info_dict.get('ext', 'mp4')
                    downloaded_file = self.find_downloaded_file(video_title, video_ext)
                    
                    if downloaded_file:
                        self.download_manager.update_download(
                            self.download_id,
                            status='completed',
                            progress=100,
                            output_file=downloaded_file
                        )
                        
                        # Set the current timestamp for the downloaded file with additional verification
                        if self.set_current_timestamp(downloaded_file):
                            self.finished_signal.emit(downloaded_file)
                        else:
                            # Even if timestamp fails, still consider download successful
                            print(f"Warning: Failed to set timestamp for {downloaded_file}")
                            self.finished_signal.emit(downloaded_file)
                    else:
                        raise Exception("Không tìm thấy file đã tải xuống")
                    
        except Exception as e:
            if self.is_cancelled:
                print("Download was cancelled by user")
                return
                
            error_message = str(e)
            # Check if the error is related to file already existing
            if "already exists" in error_message.lower() or "file exists" in error_message.lower():
                # Try to extract the filename from the error message
                try:
                    # Extract path between quotes if present
                    import re
                    match = re.search(r'"([^"]+)"', error_message)
                    if match:
                        file_path = match.group(1)
                        if os.path.exists(file_path):
                            self.file_exists_signal.emit(file_path)
                            return
                except:
                    pass
                
                # If we couldn't extract the path, emit a generic error
                self.file_exists_signal.emit("Unknown file")
                return
                
            # Handle other types of errors
            self.download_manager.update_download(
                self.download_id,
                status='error',
                error_message=error_message
            )
            self.error_signal.emit(error_message)
    
    def check_for_existing_file(self, title):
        """Check if a file with this name already exists in the output directory"""
        safe_title = clean_filename(title)
        
        # Look for files with similar names in output directory
        for file_name in os.listdir(self.output_path):
            file_path = os.path.join(self.output_path, file_name)
            if os.path.isfile(file_path) and safe_title in file_name:
                if self.format_id == 'bestaudio' and file_name.endswith('.mp3'):
                    return file_path
                elif self.format_id != 'bestaudio' and (file_name.endswith('.mp4') or file_name.endswith('.webm')):
                    return file_path
        
        return None
    
    def handle_existing_files(self, title):
        """Check if files with similar name already exist and handle appropriately"""
        try:
            # Generate base filename pattern
            base_name = clean_filename(title)
            existing_files = []
            
            # Check if any file with this name pattern exists
            for file in os.listdir(self.output_path):
                if base_name in file:
                    file_path = os.path.join(self.output_path, file)
                    if os.path.isfile(file_path):
                        existing_files.append(file)
            
            # If there are existing files, prompt the user
            if existing_files:
                # For now, just print a message - in a real application, show UI dialog
                print(f"Warning: Found {len(existing_files)} existing files with similar names")
                # We'll handle prompting the user in the UI later
        except Exception as e:
            print(f"Error checking for existing files: {str(e)}")

    def find_downloaded_file(self, video_title, video_ext):
        """Try to find the downloaded file using multiple strategies"""
        # 1. Try to find the file by scanning the output directory
        files = os.listdir(self.output_path)
        # Sort by creation time, newest first
        files.sort(key=lambda x: os.path.getctime(os.path.join(self.output_path, x)), reverse=True)
        
        # First try: Look for files with the video title in the name
        for file in files:
            file_path = os.path.join(self.output_path, file)
            # If file was created in the last 30 seconds and has the video title
            if (time.time() - os.path.getctime(file_path) < 30 and 
                (video_title.lower() in file.lower() or 
                 any(kw.lower() in file.lower() for kw in video_title.lower().split()))):
                return file_path
        
        # Second try: Just use the newest file if it was created recently
        if files:
            newest_file = files[0]  # Already sorted, first is newest
            file_path = os.path.join(self.output_path, newest_file)
            if time.time() - os.path.getctime(file_path) < 30:  # Increased from 10 seconds to 30
                return file_path
                
        return None
    
    def progress_hook(self, d):
        if self.is_cancelled:
            raise Exception("Download cancelled")
            
        if d['status'] == 'downloading':
            # Existing progress calculation
            total_bytes = d.get('total_bytes')
            total_bytes_estimate = d.get('total_bytes_estimate')
            
            total_size = total_bytes or total_bytes_estimate or 0
            downloaded_bytes = d.get('downloaded_bytes', 0)
            
            if total_size > 0:
                percent = int((downloaded_bytes / total_size) * 100)
            else:
                percent = 0
                
            # Format speed
            speed = d.get('speed', 0) or 0
            if speed < 1024:
                speed_str = f"{speed:.1f} B/s"
            elif speed < 1024 * 1024:
                speed_str = f"{speed/1024:.1f} KB/s"
            else:
                speed_str = f"{speed/(1024*1024):.1f} MB/s"
            # Format downloaded size
            if downloaded_bytes < 1024 * 1024:
                downloaded_str = f"{downloaded_bytes/1024:.1f} KB"
            else:
                downloaded_str = f"{downloaded_bytes/(1024*1024):.1f} MB"
            
            # Format total size
            if total_size < 1024 * 1024:
                total_size_str = f"{total_size/1024:.1f} KB"
            else:
                total_size_str = f"{total_size/(1024*1024):.1f} MB"
                
            # Format ETA
            eta = d.get('eta', 0) or 0
            if eta < 60:
                eta_str = f"{eta}s"
            elif eta < 3600:
                eta_str = f"{eta//60}m {eta%60}s"
            else:
                eta_str = f"{eta//3600}h {(eta%3600)//60}m"
            # Update both the UI and the download manager
            self.progress_signal.emit(percent, speed_str, f"{downloaded_str} / {total_size_str}", eta_str, total_size_str)
            
            self.download_manager.update_download(
                self.download_id,
                progress=percent,
                speed=speed_str,
                downloaded=downloaded_str,
                total_size=total_size_str,
                remaining_time=eta_str
            )
            
    def format_speed(self, speed):
        """Format download speed as string"""
        if not speed:
            return "-- KB/s"
        # If speed is already a string, just return it
        if isinstance(speed, str):
            return speed
            
        # Make sure speed is a number
        try:
            speed_value = float(speed)
        except (ValueError, TypeError):
            return "-- KB/s"
            
        # Format speed based on value
        if speed_value < 1024 * 1024:
            return f"{speed_value / 1024:.1f} KB/s"
        else:
            return f"{speed_value / 1024 / 1024:.1f} MB/s"
    
    def ensure_ytdlp_installed(self):
        try:
            import yt_dlp
        except ImportError:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
            except Exception as e:
                self.error_signal.emit(f"Không thể cài đặt yt-dlp: {str(e)}")
                raise
    
    def ensure_ffmpeg_installed(self):
        """Đảm bảo ffmpeg đã được cài đặt"""
        try:
            # Import compatibility module to ensure FFmpeg is properly set up
            from utils import compat
            
            # First check if FFmpeg is available through our compatibility layer
            ffmpeg_available, ffmpeg_path = compat.ensure_ffmpeg_available()
            if ffmpeg_available:
                if ffmpeg_path:
                    os.environ["FFMPEG_LOCATION"] = ffmpeg_path
                    path_dir = os.path.dirname(ffmpeg_path)
                    if path_dir not in os.environ.get("PATH", ""):
                        os.environ["PATH"] = path_dir + os.pathsep + os.environ.get("PATH", "")
                return True  # Return True to indicate success
            
            # Fallback to checking system PATH
            subprocess.check_call(['ffmpeg', '-version'], 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)
            return True  # Return True if ffmpeg is in PATH
        except (subprocess.SubprocessError, FileNotFoundError):
            # Fix: Use progress_signal instead of progress
            self.progress_signal.emit(0, "Đang kiểm tra FFmpeg...", "", "", "")
            try:
                # Try finding ffmpeg through yt-dlp's mechanism
                import yt_dlp
                if hasattr(yt_dlp.utils, 'get_exe_dir'):
                    ffmpeg_location = yt_dlp.utils.get_exe_dir()
                    if ffmpeg_location:
                        ffmpeg_exe = 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg'
                        if os.path.exists(os.path.join(ffmpeg_location, ffmpeg_exe)):
                            os.environ["PATH"] += os.pathsep + ffmpeg_location
                            return True  # Return True if found through yt-dlp
                
                # If not found, notify user but continue (some functionality might still work)
                self.progress_signal.emit(10, "FFmpeg không tìm thấy, một số tính năng có thể bị hạn chế...", "", "", "")
                return False  # Return False to indicate FFmpeg wasn't found
            except Exception as e:
                self.progress_signal.emit(10, f"FFmpeg không tìm thấy: {str(e)}", "", "", "")
                return False  # Return False on any error

    def set_current_timestamp(self, file_path):
        """Set the file creation and modification time to current time"""
        try:
            if not os.path.exists(file_path):
                print(f"Warning: Cannot set timestamp - file does not exist: {file_path}")
                return False
                
            # Try multiple approaches to set the timestamp
            current_time = time.time()
            success = False
            
            # Method 1: Use os.utime to set access and modification times
            try:
                os.utime(file_path, (current_time, current_time))
                success = True
                print(f"Set modified/access time of {file_path}")
            except Exception as e:
                print(f"Error setting timestamp with os.utime: {str(e)}")
            
            # Method 2: On Windows, also try to set creation time using win32 API
            if os.name == 'nt':
                try:
                    import win32file, win32con, pywintypes
                    handle = win32file.CreateFile(
                        file_path, 
                        win32con.GENERIC_WRITE,
                        win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                        None, 
                        win32con.OPEN_EXISTING,
                        win32con.FILE_ATTRIBUTE_NORMAL, 
                        None
                    )
                    win_time = pywintypes.Time(int(current_time))
                    win32file.SetFileTime(handle, win_time, win_time, win_time)
                    handle.close()
                    success = True
                    print(f"Set all timestamps of {file_path} using win32 API")
                except ImportError:
                    print("Warning: win32file module not available")
                except Exception as e:
                    print(f"Error setting timestamp with win32file: {str(e)}")
            
            # Method 3: Last resort - use PowerShell to set creation time on Windows
            if not success and os.name == 'nt':
                try:
                    import subprocess
                    timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(current_time))
                    
                    # Properly escape path for PowerShell - handle spaces and special characters
                    escaped_path = file_path.replace("'", "''").replace("\\", "\\\\")
                    cmd = f'powershell -Command "(Get-Item \'{escaped_path}\').CreationTime = \'{timestamp_str}\'"'
                    
                    subprocess.run(cmd, shell=True, check=False)
                    print(f"Set creation time of {file_path} using PowerShell")
                    success = True
                except Exception as e:
                    print(f"Error setting timestamp with PowerShell: {str(e)}")
            
            return success
        except Exception as e:
            print(f"Error in set_current_timestamp: {str(e)}")
            return False
    
    def cleanup_temp_files(self, directory, main_file_name):
        """Dọn dẹp tất cả các file tạm thời và phần còn lại"""
        try:
            # Tìm tất cả các file có thể là file tạm
            base_name = os.path.splitext(main_file_name)[0]
            for filename in os.listdir(directory):
                # Kiểm tra các file tạm liên quan đến file chính
                if filename != main_file_name and (
                    filename.endswith('.part') or 
                    filename.endswith('.temp') or 
                    filename.endswith('.webm.part') or
                    (base_name in filename and filename.endswith('.webm')) or
                    (base_name in filename and filename.endswith('.m4a')) or
                    (base_name in filename and filename.endswith('.f*')) or
                    filename.endswith('.ytdl')
                ):
                    try:
                        file_path = os.path.join(directory, filename)
                        os.remove(file_path)
                        print(f"Cleaned up temp file: {file_path}")
                    except Exception as e:
                        print(f"Failed to delete temp file {filename}: {str(e)}")
            
            # Thêm đợi một chút để đảm bảo các ứng dụng khác đã giải phóng file
            time.sleep(0.5)
                
        except Exception as e:
            print(f"Error cleaning up temp files: {str(e)}")

    def stop(self, pause=True):
        """Stop the download thread, optionally setting status to paused"""
        self.is_cancelled = True
        # Only change status if specifically requesting to pause
        if pause:
            self.download_manager.update_download(
                self.download_id,
                status='paused'
            )

class VideoInfoThread(QThread):
    info_ready = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url
        self.should_stop = False

    def clean_url(self, url):
        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        if 'v' in query_params:
            video_id = query_params['v'][0]
            clean_query = urllib.parse.urlencode({'v': video_id})
            return urllib.parse.urlunparse((
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                parsed_url.params,
                clean_query,
                ''
            ))
        return url

    def run(self):
        try:
            self.url = self.clean_url(self.url)
            self.progress.emit("Đang làm sạch URL...")
            
            self.progress.emit("Kiểm tra thư viện yt-dlp...")
            self.ensure_ytdlp_installed()
            import yt_dlp
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 15,
                'extract_flat': False,
            }
            
            self.progress.emit("Đang tải thông tin video từ YouTube...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if self.should_stop:
                    return
                
                self.progress.emit("Trích xuất thông tin cơ bản...")
                basic_info = ydl.extract_info(self.url, download=False, process=False)
                
                if basic_info.get('_type') == 'playlist':
                    if not basic_info.get('entries'):
                        raise Exception("Không tìm thấy video trong playlist")
                    entry = basic_info['entries'][0]
                    if 'url' in entry or 'id' in entry:
                        video_id = entry.get('id', entry.get('url', ''))
                        self.url = f"https://www.youtube.com/watch?v={video_id}"
                        self.progress.emit(f"Phát hiện playlist, chuyển đến video: {video_id}")
                        info_dict = ydl.extract_info(self.url, download=False, process=True)
                    else:
                        raise Exception("Không thể xác định URL video từ playlist")
                else:
                    self.progress.emit("Trích xuất thông tin chi tiết...")
                    info_dict = ydl.extract_info(self.url, download=False, process=True)
                
                if self.should_stop:
                    return
                
                formats = []
                
                # Thêm tùy chọn tải video chất lượng cao nhất
                formats.append({
                    'format_id': 'best',
                    'ext': 'mp4',
                    'display_name': 'Video Chất Lượng Cao Nhất',
                    'is_audio': False,
                    'is_best': True
                })
                
                # Thêm tùy chọn audio với các chất lượng khác nhau
                formats.append({
                    'format_id': 'bestaudio/best',
                    'ext': 'mp3',
                    'display_name': 'Audio MP3 (320kbps)',
                    'is_audio': True,
                    'audio_quality': '320'
                })
                
                formats.append({
                    'format_id': 'bestaudio/best',
                    'ext': 'mp3',
                    'display_name': 'Audio MP3 (192kbps)',
                    'is_audio': True,
                    'audio_quality': '192'
                })
                
                formats.append({
                    'format_id': 'bestaudio/best',
                    'ext': 'mp3',
                    'display_name': 'Audio MP3 (128kbps)',
                    'is_audio': True,
                    'audio_quality': '128'
                })
                
                self.progress.emit("Tổng hợp các định dạng tải xuống...")
                video_formats = {}
                for f in info_dict.get('formats', []):
                    if self.should_stop:
                        return
                    
                    # Chỉ lọc các format video chính
                    if f.get('vcodec') != 'none' and f.get('height'):
                        height = f.get('height')
                        # Nhóm các format theo độ phân giải và ưu tiên format có audio
                        has_audio = f.get('acodec') != 'none'
                        
                        # Ưu tiên format có cả audio và video
                        if height not in video_formats or (has_audio and not video_formats[height].get('acodec', 'none') != 'none'):
                            video_formats[height] = f
                
                common_resolutions = [144, 240, 360, 480, 720, 1080, 1440, 2160]
                for height in sorted(video_formats.keys()):
                    if height in common_resolutions:
                        f = video_formats[height]
                        format_id = f['format_id']
                        formats.append({
                            'format_id': format_id,
                            'ext': 'mp4',
                            'display_name': f"{height}p ({f.get('ext', 'mp4')})",
                            'is_audio': False
                        })
                
                if len(formats) <= 1:
                    self.progress.emit("Không tìm thấy định dạng video phù hợp...")
                    for f in info_dict.get('formats', []):
                        if f.get('ext') in ['mp4', 'webm'] and f.get('height') and f.get('vcodec') != 'none':
                            format_id = f['format_id']
                            height = f.get('height')
                            formats.append({
                                'format_id': format_id,
                                'ext': f.get('ext', 'mp4'),
                                'display_name': f"{height}p ({f.get('ext', 'mp4')})",
                                'is_audio': False
                            })
                
                video_info = {
                    'title': info_dict.get('title', 'Unknown video'),
                    'channel': info_dict.get('uploader', 'Unknown channel'),
                    'duration': info_dict.get('duration', 0),
                    'thumbnail_url': info_dict.get('thumbnail', ''),
                    'formats': formats,
                    'default_format_index': 0  # Mặc định là chất lượng cao nhất
                }
                
                # Tìm format 1080p để đặt làm mặc định
                for i, fmt in enumerate(formats):
                    if '1080p' in fmt.get('display_name', ''):
                        video_info['default_format_index'] = i
                        break
                
                self.info_ready.emit(video_info)
                
        except Exception as e:
            self.error.emit(f"Lỗi: {str(e)}")
    
    def ensure_ytdlp_installed(self):
        try:
            import yt_dlp
        except ImportError:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
            except Exception as e:
                self.error.emit(f"Không thể cài đặt yt-dlp: {str(e)}")
                raise
    
    def stop(self):
        self.should_stop = True

class YouTubeDownloaderWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KHyTool - YouTube Downloader")
        self.setMinimumSize(900, 650)
        self.showMaximized()  # Đảm bảo mở full screen
        self.output_path = os.path.expanduser("~/Downloads")
        self.info_thread = None
        self.download_thread = None
        self.returning_to_hub = False  # Add flag to track return to hub action
        self.initUI()
        self.setStyleSheet("""
            QMainWindow {
                background-color: #FFFFFF;
            }
            QLabel {
                color: #282828;
                font-size: 14px;  /* Tăng font size */
            }
            QLabel#header {
                font-size: 32px;  /* Tăng font size từ 24px lên 32px */
                font-weight: bold;
                color: #FF0000;
            }
            QLabel#info {
                font-weight: bold;
                color: #282828;
                font-size: 16px;  /* Tăng font size từ 13px lên 16px */
            }
            QPushButton {
                background-color: #FF0000;
                color: white;
                border: none;
                border-radius: 6px;  /* Tăng độ bo tròn từ 4px lên 6px */
                padding: 12px 20px;  /* Tăng padding từ 8px 16px lên 12px 20px */
                font-weight: bold;
                font-size: 14px;  /* Thêm font size cho các nút */
            }
            QPushButton:hover {
                background-color: #CC0000;
            }
            QPushButton:pressed {
                background-color: #AA0000;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
            QPushButton#secondary {
                background-color: #282828;
                color: white;
            }
            QPushButton#secondary:hover {
                background-color: #404040;
            }
            QPushButton#secondary:pressed {
                background-color: #181818;
            }
            QPushButton#cancel {
                background-color: #F1F1F1;
                color: #282828;
            }
            QPushButton#cancel:hover {
                background-color: #E0E0E0;
            }
            QLineEdit {
                border: 1px solid #D3D3D3;
                border-radius: 6px;  /* Tăng độ bo tròn từ 4px lên 6px */
                padding: 12px;  /* Tăng padding từ 8px lên 12px */
                font-size: 16px;  /* Tăng font size từ 14px lên 16px */
            }
            QLineEdit:focus {
                border: 2px solid #FF0000;  /* Tăng độ dày viền từ 1px lên 2px */
            }
            QProgressBar {
                border: 1px solid #D3D3D3;
                border-radius: 6px;  /* Tăng độ bo tròn từ 4px lên 6px */
                text-align: center;
                height: 24px;  /* Tăng chiều cao từ 20px lên 24px */
                font-weight: bold;
                font-size: 14px;  /* Thêm font size */
            }
            QProgressBar::chunk {
                background-color: #FF0000;
                border-radius: 5px;  /* Tăng độ bo tròn từ 3px lên 5px */
            }
            QComboBox {
                border: 1px solid #D3D3D3;
                border-radius: 6px;  /* Tăng độ bo tròn từ 4px lên 6px */
                padding: 10px;  /* Tăng padding từ 6px lên 10px */
                min-width: 250px;  /* Tăng chiều rộng tối thiểu từ 200px lên 250px */
                font-size: 14px;  /* Thêm font size */
            }
            QComboBox:hover {
                border: 1px solid #A0A0A0;
            }
            QComboBox:focus {
                border: 2px solid #FF0000;  /* Tăng độ dày viền từ 1px lên 2px */
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #D3D3D3;
                border-radius: 10px;  /* Tăng độ bo tròn từ 6px lên 10px */
                margin-top: 14px;  /* Tăng margin từ 12px lên 14px */
                padding: 15px;  /* Tăng padding từ 10px lên 15px */
                font-size: 16px;  /* Thêm font size */
                background-color: #fafafa;  /* Thêm màu nền nhẹ */
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;  /* Tăng từ 10px lên 15px */
                padding: 0 10px;  /* Tăng padding ngang */
                color: #FF0000;
                background-color: #ffffff; 
            }
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #c0c0c0;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a0a0a0;
            }
        """)

    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(40, 30, 40, 30)  # Tăng padding từ 20px lên 40px và 30px
        layout.setSpacing(25)  # Tăng spacing từ 15px lên 25px

        # Header với thiết kế tối giản, chuyên nghiệp hơn
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(10, 5, 10, 5)
        
        # Header text (loại bỏ emoji logo)
        header_label = QLabel("YouTube Downloader")
        header_label.setObjectName("header")
        header_label.setAlignment(Qt.AlignCenter)
        # Tạo hiệu ứng viền nổi với màu YouTube
        header_label.setStyleSheet("""
            font-size: 36px;
            font-weight: bold;
            color: #FF0000;
            border-bottom: 3px solid #FF0000;
            padding-bottom: 5px;
        """)
        header_layout.addWidget(header_label, 1)
        
        layout.addWidget(header_widget)

        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #FF0000; min-height: 2px;")
        layout.addWidget(separator)

        # URL Input với thiết kế chuyên nghiệp hơn (không dùng emoji)
        input_group = QGroupBox("URL Video")
        input_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #FF0000;
                border-radius: 12px;
                margin-top: 16px;
                background-color: #ffffff;
                padding: 18px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
                color: #FF0000;
                background-color: #ffffff;
                font-size: 18px;
            }
        """)
        input_layout = QVBoxLayout(input_group)
        input_layout.setSpacing(15)

        link_layout = QHBoxLayout()
        
        # Loại bỏ icon và tăng trực tiếp kích thước input
        self.link_input = QLineEdit()
        self.link_input.setPlaceholderText("Nhập link YouTube...")
        self.link_input.setMinimumHeight(50)
        
        fetch_button = QPushButton("Lấy thông tin")
        fetch_button.setObjectName("secondary")
        fetch_button.setMinimumHeight(50)
        fetch_button.setMinimumWidth(150)  # Tăng chiều rộng tối thiểu
        fetch_button.clicked.connect(self.fetch_video_info)
        
        link_layout.addWidget(self.link_input)
        link_layout.addWidget(fetch_button)
        input_layout.addLayout(link_layout)
        
        # Thêm gợi ý sử dụng
        hint_label = QLabel("Ví dụ: https://www.youtube.com/watch?v=abc123")
        hint_label.setStyleSheet("font-size: 14px; color: #777777; font-style: italic;")
        input_layout.addWidget(hint_label)
        
        layout.addWidget(input_group)

        # Video Info Panel - cải thiện hiển thị
        info_group = QGroupBox("Thông tin Video")
        info_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #E62117;
                border-radius: 12px;
                margin-top: 16px;
                background-color: #ffffff;
                padding: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
                color: #E62117;
                background-color: #ffffff;
                font-size: 18px;
            }
        """)
        
        info_layout = QHBoxLayout(info_group)
        info_layout.setSpacing(20)  # Giảm khoảng cách giữa các phần tử

        # Thumbnail frame - Điều chỉnh kích thước
        thumbnail_frame = QFrame()
        thumbnail_frame.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border: 2px solid #E62117;
                border-radius: 10px;
                padding: 2px;
            }
        """)
        thumbnail_layout = QVBoxLayout(thumbnail_frame)
        thumbnail_layout.setContentsMargins(0, 0, 0, 0)
        
        # Chuẩn hóa kích thước thumbnail theo tỷ lệ YouTube
        self.thumbnail_label = QLabel("Thumbnail sẽ hiển thị ở đây")
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setFixedSize(320, 180)  # Kích thước chuẩn 16:9
        self.thumbnail_label.setScaledContents(True)
        self.thumbnail_label.setStyleSheet("""
            border: none; 
            background: transparent;
            font-size: 16px;
            color: #666;
            qproperty-alignment: AlignCenter;
        """)
        thumbnail_layout.addWidget(self.thumbnail_label, 0, Qt.AlignCenter)
        
        # Thêm thumbnail vào layout với kích thước cố định
        info_layout.addWidget(thumbnail_frame, 0, Qt.AlignLeft | Qt.AlignTop)
        
        # Khung thông tin chi tiết bên phải thumbnail
        details_frame = QFrame()
        details_frame.setStyleSheet("background-color: #f9f9f9; border-radius: 8px;")
        details_layout = QVBoxLayout(details_frame)
        details_layout.setSpacing(15)  # Khoảng cách giữa các nhãn
        
        # Title - không dùng icon, dùng label style thay thế
        self.title_label = QLabel("Tiêu đề: ")
        self.title_label.setObjectName("info")
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #282828;
            padding: 8px;
            background-color: #f0f0f0;
            border-left: 4px solid #E62117;
            min-height: 20px;
        """)
        self.title_label.setMinimumHeight(50)
        details_layout.addWidget(self.title_label)
        
        # Channel
        self.channel_label = QLabel("Kênh: ")
        self.channel_label.setObjectName("info")
        self.channel_label.setWordWrap(True)
        self.channel_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #282828;
            padding: 8px;
            background-color: #f0f0f0;
            border-left: 4px solid #0099FF;
            min-height: 20px;
        """)
        self.channel_label.setMinimumHeight(40)
        details_layout.addWidget(self.channel_label)
        
        # Duration
        self.duration_label = QLabel("Thời lượng: ")
        self.duration_label.setObjectName("info")
        self.duration_label.setWordWrap(True)
        self.duration_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #282828;
            padding: 8px;
            background-color: #f0f0f0;
            border-left: 4px solid #FFD700;
            min-height: 20px;
        """)
        self.duration_label.setMinimumHeight(40)
        details_layout.addWidget(self.duration_label)
        
        # Thêm stretch để đẩy các phần tử lên trên
        details_layout.addStretch(1)
        
        # Thêm khung thông tin vào layout chính
        info_layout.addWidget(details_frame, 1)
        
        # Khung chọn chất lượng bên phải cùng
        quality_frame = QFrame()
        quality_frame.setStyleSheet("background-color: #f0f0f0; border-radius: 8px; padding: 10px;")
        quality_layout = QVBoxLayout(quality_frame)
        quality_layout.setSpacing(10)
        
        # Label cho phần chọn chất lượng
        quality_label = QLabel("CHỌN CHẤT LƯỢNG")
        quality_label.setAlignment(Qt.AlignCenter)
        quality_label.setStyleSheet("font-weight: bold; color: #4CAF50; font-size: 15px;")
        quality_layout.addWidget(quality_label)
        
        # Format selection
        self.format_combo = QComboBox()
        self.format_combo.setMinimumHeight(45)
        self.format_combo.setMinimumWidth(200)  # Đảm bảo đủ rộng
        self.format_combo.setFont(QFont("Arial", 14))
        self.format_combo.setPlaceholderText("Chọn chất lượng")
        self.format_combo.setEnabled(False)  # Disabled mặc định khi chưa có video
        self.format_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #D3D3D3;
                border-radius: 6px;
                padding: 10px;
                font-size: 14px;
                background-color: #f8f8f8;
                border-left: 4px solid #4CAF50;
                color: #333333;
            }
            QComboBox:hover:enabled {
                border: 1px solid #A0A0A0;
            }
            QComboBox:focus {
                border: 2px solid #FF0000;
            }
            QComboBox::placeholder {
                color: #888888;
                font-style: italic;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 25px;
                border-left-width: 1px;
                border-left-color: #D3D3D3;
                border-left-style: solid;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QComboBox::down-arrow {
                image: none;
                width: 14px;
                height: 14px;
                background: #333333;
            }
            QComboBox:disabled {
                background-color: #E5E5E5;
                color: #888888;
                border-color: #CCCCCC;
                border-left: 4px solid #AAAAAA;
            }
            QComboBox::drop-down:disabled {
                border-left-color: #CCCCCC;
            }
            QComboBox::down-arrow:disabled {
                background: #AAAAAA;
            }
        """)
        quality_layout.addWidget(self.format_combo)
        
        # Thêm stretch để đẩy các phần tử lên trên
        quality_layout.addStretch(1)
        
        # Thêm khung chọn chất lượng vào layout chính
        info_layout.addWidget(quality_frame, 0)
        
        layout.addWidget(info_group)

        # Output Path Selection - modern style
        path_group = QGroupBox("Đường dẫn xuất file")
        path_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #D3D3D3;
                border-radius: 12px;
                margin-top: 16px;
                background-color: #ffffff;
                padding: 18px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
                color: #555555;
                background-color: #ffffff;
                font-size: 18px;
            }
        """)
        
        path_layout = QHBoxLayout(path_group)
        path_layout.setSpacing(15)
        
        # Loại bỏ icon thư mục
        self.path_label = QLabel(f"Đường dẫn tải về: {self.output_path}")
        self.path_label.setFont(QFont("Arial", 14))
        self.path_label.setStyleSheet("background-color: #f5f5f5; padding: 10px; border-radius: 6px;")
        
        path_button = QPushButton("Chọn thư mục")
        path_button.setObjectName("secondary")
        path_button.setMinimumHeight(45)
        path_button.setMinimumWidth(150)  # Tăng chiều rộng tối thiểu
        path_button.setFont(QFont("Arial", 14))
        path_button.setCursor(Qt.PointingHandCursor)
        path_button.clicked.connect(self.select_output_path)
        
        path_layout.addWidget(self.path_label, 1)
        path_layout.addWidget(path_button)
        layout.addWidget(path_group)

        # Download Button - Lớn và nổi bật
        self.download_button = QPushButton("TẢI XUỐNG")
        self.download_button.setMinimumHeight(60)
        self.download_button.setFont(QFont("Arial", 18, QFont.Bold))
        self.download_button.setStyleSheet("""
            QPushButton {
                background-color: #FF0000;
                color: white;
                border-radius: 8px;
                padding: 15px 30px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #CC0000;
            }
            QPushButton:pressed {
                background-color: #AA0000;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """)
        self.download_button.clicked.connect(self.download_video)
        self.download_button.setEnabled(False)
        layout.addWidget(self.download_button)

        # Progress Section - loại bỏ icons, thiết kế chuyên nghiệp
        progress_group = QGroupBox("Tiến độ tải xuống")
        progress_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4CAF50;
                border-radius: 12px;
                margin-top: 16px;
                background-color: #ffffff;
                padding: 18px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
                color: #4CAF50;
                background-color: #ffffff;
                font-size: 18px;
            }
        """)
        
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setSpacing(15)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimumHeight(30)
        self.progress_bar.setFont(QFont("Arial", 14))
        progress_layout.addWidget(self.progress_bar)
        
        # Khu vực thông tin - thiết kế theo grid để gọn gàng hơn
        progress_info_frame = QFrame()
        progress_info_frame.setStyleSheet("background-color: #f5f5f5; border-radius: 8px; padding: 15px;")
        progress_info_layout = QHBoxLayout(progress_info_frame)
        progress_info_layout.setSpacing(30)  # Tăng spacing
        
        # Thông tin tốc độ - không dùng icon
        speed_container = QWidget()
        speed_container_layout = QVBoxLayout(speed_container)
        speed_container_layout.setContentsMargins(0, 0, 0, 0)
        
        speed_header = QLabel("TỐC ĐỘ")
        speed_header.setAlignment(Qt.AlignCenter)
        speed_header.setStyleSheet("font-weight: bold; color: #2196F3; font-size: 14px;")
        speed_container_layout.addWidget(speed_header)
        
        self.speed_label = QLabel("-- KB/s")
        self.speed_label.setFont(QFont("Arial", 16, QFont.Bold))  # Tăng kích thước font
        self.speed_label.setAlignment(Qt.AlignCenter)
        self.speed_label.setStyleSheet("color: #2196F3;")
        speed_container_layout.addWidget(self.speed_label)
        
        progress_info_layout.addWidget(speed_container, 1)
        
        # Thông tin tiến độ - không dùng icon
        progress_container = QWidget()
        progress_container_layout = QVBoxLayout(progress_container)
        progress_container_layout.setContentsMargins(0, 0, 0, 0)
        
        progress_header = QLabel("KÍCH THƯỚC")
        progress_header.setAlignment(Qt.AlignCenter)
        progress_header.setStyleSheet("font-weight: bold; color: #4CAF50; font-size: 14px;")
        progress_container_layout.addWidget(progress_header)
        
        self.downloaded_label = QLabel("-- / --")
        self.downloaded_label.setFont(QFont("Arial", 16, QFont.Bold))  # Tăng kích thước font
        self.downloaded_label.setAlignment(Qt.AlignCenter)
        self.downloaded_label.setStyleSheet("color: #4CAF50;")
        progress_container_layout.addWidget(self.downloaded_label)
        
        progress_info_layout.addWidget(progress_container, 1)
        
        # Thông tin thời gian - không dùng icon
        time_container = QWidget()
        time_container_layout = QVBoxLayout(time_container)
        time_container_layout.setContentsMargins(0, 0, 0, 0)
        
        time_header = QLabel("THỜI GIAN CÒN LẠI")
        time_header.setAlignment(Qt.AlignCenter)
        time_header.setStyleSheet("font-weight: bold; color: #FF9800; font-size: 14px;")
        time_container_layout.addWidget(time_header)
        
        self.time_label = QLabel("--")
        self.time_label.setFont(QFont("Arial", 16, QFont.Bold))  # Tăng kích thước font
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("color: #FF9800;")
        time_container_layout.addWidget(self.time_label)
        
        progress_info_layout.addWidget(time_container, 1)
        
        progress_layout.addWidget(progress_info_frame)
        layout.addWidget(progress_group)
        
        # Ẩn progress group ban đầu
        progress_group.setVisible(False)
        self.progress_group = progress_group

        # Footer - thiết kế tối giản
        footer_widget = QWidget()
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 15, 0, 0)
        
        # Version info
        version_label = QLabel("v1.0")
        version_label.setStyleSheet("color: #888; font-style: italic;")
        footer_layout.addWidget(version_label)
        
        footer_layout.addStretch(1)
        
        # Nút trở về - không sử dụng icon
        back_to_hub_btn = QPushButton("Quay về Tool Hub")
        back_to_hub_btn.setObjectName("secondary")
        back_to_hub_btn.setMinimumHeight(45)
        back_to_hub_btn.setMinimumWidth(200)
        back_to_hub_btn.setFont(QFont("Arial", 14))
        back_to_hub_btn.clicked.connect(self.back_to_tool_hub)
        footer_layout.addWidget(back_to_hub_btn)
        
        layout.addWidget(footer_widget)

        # Status Bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("QStatusBar { color: #282828; font-size: 14px; padding: 5px; }")
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Sẵn sàng tải xuống video từ YouTube")

    def fetch_video_info(self):
        """Fetch video information from YouTube"""
        url = self.link_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập link YouTube")
            return
        
        # Check if URL is a YouTube URL
        if "youtube.com" not in url and "youtu.be" not in url:
            QMessageBox.warning(self, "URL không hợp lệ", "URL không phải là link YouTube. Vui lòng kiểm tra lại.")
            return
        
        # Cancel previous thread if running
        if self.info_thread and self.info_thread.isRunning():
            self.info_thread.stop()
            self.info_thread.wait()
        
        # Update UI to show loading state
        self.thumbnail_label.setText("Đang tải thông tin...")
        self.title_label.setText("Tiêu đề: Đang tải...")
        self.channel_label.setText("Kênh: Đang tải...")
        self.duration_label.setText("Thời lượng: Đang tải...")
        self.format_combo.clear()
        self.format_combo.setEnabled(False)  # Vô hiệu hóa combo box khi đang tải
        self.format_combo.setPlaceholderText("Đang tải danh sách chất lượng...")
        self.download_button.setEnabled(False)
        
        # Create and start thread to fetch video info
        self.info_thread = VideoInfoThread(url)
        self.info_thread.info_ready.connect(self.update_video_info)
        self.info_thread.error.connect(self.handle_info_error)
        self.info_thread.progress.connect(self.update_status)
        self.info_thread.start()
        
        self.status_bar.showMessage("Đang tải thông tin video...")

    def update_video_info(self, info):
        """Update UI with video information"""
        # Giới hạn độ dài tiêu đề để tránh lỗi hiển thị
        title = info['title']
        if len(title) > 80:  # Giới hạn độ dài hiển thị
            title = title[:77] + "..."
            
        # Update title
        self.title_label.setText(f"Tiêu đề: {title}")
        
        # Giới hạn độ dài tên kênh
        channel = info['channel']
        if len(channel) > 50:  # Giới hạn độ dài hiển thị
            channel = channel[:47] + "..."
            
        # Update channel
        self.channel_label.setText(f"Kênh: {channel}")
        
        # Update duration
        duration_str = format_time(info['duration'])
        self.duration_label.setText(f"Thời lượng: {duration_str}")
        
        # Load thumbnail
        if info['thumbnail_url']:
            try:
                response = requests.get(info['thumbnail_url'])
                if response.status_code == 200:
                    pixmap = QPixmap()
                    pixmap.loadFromData(response.content)
                    self.thumbnail_label.setPixmap(pixmap.scaled(
                        self.thumbnail_label.width(),
                        self.thumbnail_label.height(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    ))
            except Exception as e:
                self.status_bar.showMessage(f"Không thể tải thumbnail: {str(e)}")
        
        # Update format combo box
        self.format_combo.clear()
        self.format_combo.setEnabled(True)  # Kích hoạt combo box khi có thông tin video
        self.format_combo.setPlaceholderText("Chọn chất lượng")
        for fmt in info['formats']:
            self.format_combo.addItem(fmt['display_name'], fmt['format_id'])
        
        # Set default format
        if 'default_format_index' in info and 0 <= info['default_format_index'] < len(info['formats']):
            self.format_combo.setCurrentIndex(info['default_format_index'])
        
        # Enable download button
        self.download_button.setEnabled(True)
        self.status_bar.showMessage(f"Đã tải thông tin video: {info['title']}")

    def handle_info_error(self, error):
        """Handle errors during info fetching"""
        self.thumbnail_label.setText("Không thể tải thông tin video")
        self.title_label.setText("Tiêu đề: --")
        self.channel_label.setText("Kênh: --")
        self.duration_label.setText("Thời lượng: --")
        self.format_combo.clear()
        self.format_combo.setEnabled(False)  # Vô hiệu hóa combo box khi có lỗi
        self.format_combo.setPlaceholderText("Chọn chất lượng")
        self.download_button.setEnabled(False)
        self.status_bar.showMessage(f"Lỗi: {error}")
        QMessageBox.critical(self, "Lỗi", f"Không thể tải thông tin video: {error}")

    def update_status(self, message):
        """Update status bar with progress message"""
        self.status_bar.showMessage(message)

    def select_output_path(self):
        """Select output directory"""
        path = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu video", self.output_path)
        if path:
            self.output_path = path
            self.path_label.setText(f"Đường dẫn tải về: {self.output_path}")

    def download_video(self):
        """Download video with selected format"""
        url = self.link_input.text().strip()
        format_id = self.format_combo.currentData()
        
        if not url:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập link YouTube")
            return
        
        if not format_id:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn định dạng tải xuống")
            return
        
        # Check write permission on output directory
        try:
            test_file = os.path.join(self.output_path, ".write_test")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi quyền truy cập", 
                f"Không thể ghi vào thư mục đầu ra: {self.output_path}\nLỗi: {str(e)}")
            return
        
        # Cancel previous download if running
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.stop()
            self.download_thread.wait()
        
        # Reset progress bar
        self.progress_bar.setValue(0)
        self.speed_label.setText("-- KB/s")
        self.downloaded_label.setText("-- / --")
        self.time_label.setText("--")
        self.progress_group.setVisible(True)
        
        # Create cancel button if not exists
        if not hasattr(self, 'cancel_button'):
            self.cancel_button = QPushButton("Hủy tải xuống")
            self.cancel_button.setObjectName("cancel")
            self.cancel_button.clicked.connect(self.cancel_download)
            # Insert cancel button before progress group
            layout_index = self.centralWidget().layout().indexOf(self.progress_group)
            self.centralWidget().layout().insertWidget(layout_index, self.cancel_button)
        else:
            self.cancel_button.setVisible(True)
        
        # Create and start download thread
        self.download_thread = DownloadThread(url, format_id, self.output_path)
        self.download_thread.progress_signal.connect(self.update_download_progress)
        self.download_thread.finished_signal.connect(self.download_finished)
        self.download_thread.error_signal.connect(self.download_error)
        # Add new connection for file exists signal
        self.download_thread.file_exists_signal.connect(self.handle_file_exists)
        self.download_thread.start()
        
        # Update UI
        self.download_button.setText("Đang tải...")
        self.download_button.setEnabled(False)
        self.status_bar.showMessage("Đang tải xuống video...")

    def cancel_download(self):
        """Cancel current download"""
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.stop(pause=True)  # Explicitly pause when cancelling
            self.status_bar.showMessage("Đang hủy tải xuống...")
            QTimer.singleShot(1000, self.reset_download_ui)

    def reset_download_ui(self):
        """Reset UI after download is cancelled or completed"""
        self.download_button.setText("TẢI XUỐNG")
        self.download_button.setEnabled(True)
        
        # Hide progress group and cancel button
        self.progress_group.setVisible(False)
        if hasattr(self, 'cancel_button'):
            self.cancel_button.setVisible(False)

    def update_download_progress(self, percent, speed, downloaded, remaining_time, total_size):
        """Update progress UI"""
        self.progress_bar.setValue(percent)
        self.speed_label.setText(speed)
        self.downloaded_label.setText(downloaded)
        self.time_label.setText(remaining_time)
        self.setWindowTitle(f"YouTube Downloader - {percent}%")

    def download_finished(self, file_path):
        """Handle successful download"""
        self.status_bar.showMessage(f"Tải xuống hoàn tất: {os.path.basename(file_path)}")
        self.reset_download_ui()
        self.setWindowTitle("KHyTool - YouTube Downloader")
        
        # Show success message with option to open folder
        reply = QMessageBox.question(
            self,
            "Tải xuống hoàn tất",
            f"Tải xuống video thành công!\n\nTệp: {os.path.basename(file_path)}\n\nBạn có muốn mở thư mục chứa file không?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.open_folder(file_path)

    def open_folder(self, file_path):
        """Open folder containing the downloaded file"""
        try:
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "Lỗi", f"Không tìm thấy file: {file_path}")
                return
            
            # Get the directory path
            dir_path = os.path.dirname(file_path)
            
            if os.name == 'nt':  # Windows
                os.startfile(dir_path)
            elif os.name == 'posix':  # macOS, Linux
                subprocess.Popen(['xdg-open', dir_path])
            
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể mở thư mục: {str(e)}")

    def handle_file_exists(self, file_path):
        """Handle case when file already exists"""
        # Reset UI
        self.reset_download_ui()
        self.setWindowTitle("KHyTool - YouTube Downloader")
        
        # Show message to user with larger size
        file_name = os.path.basename(file_path) if file_path != "Unknown file" else "Unknown"
        message_box = QMessageBox(self)
        message_box.setIcon(QMessageBox.Information)
        message_box.setWindowTitle("File Already Exists")
        message_box.setText(f"File đã tồn tại:\n{file_name}")
        message_box.setInformativeText("Bạn có muốn mở thư mục chứa file này?")
        message_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        message_box.setDefaultButton(QMessageBox.Yes)
        
        # Make the message box larger
        message_box.setStyleSheet("""
            QMessageBox {
                min-width: 500px;
                min-height: 200px;
            }
            QLabel {
                font-size: 14px;
                min-width: 450px;
            }
            QPushButton {
                width: 100px;
                height: 30px;
                font-size: 14px;
            }
        """)
        
        # Manually set a larger font for the text
        font = message_box.font()
        font.setPointSize(12)
        message_box.setFont(font)
        
        reply = message_box.exec_()
        if reply == QMessageBox.Yes and file_path != "Unknown file":
            self.open_folder(file_path)

    def download_error(self, error):
        """Handle download error"""
        self.status_bar.showMessage(f"Lỗi: {error}")
        self.reset_download_ui()
        self.setWindowTitle("KHyTool - YouTube Downloader")
        QMessageBox.critical(self, "Lỗi tải xuống", f"Không thể tải xuống video: {error}")

    def back_to_tool_hub(self):
        """Return to main menu without stopping downloads"""
        # Set flag to indicate we're returning to hub (don't stop downloads)
        self.returning_to_hub = True
        
        # Don't stop running threads - let them continue in the background
        # Only stop the info thread which is just for UI updates
        if self.info_thread and self.info_thread.isRunning():
            self.info_thread.stop()
            self.info_thread.wait()
        
        # Navigate back to main menu
        from ui.main_menu import MainMenu
        self.main_menu = MainMenu()
        self.main_menu.show()
        self.close()
        
    def closeEvent(self, event):
        """Handle window close event"""
        # Stop running threads
        if self.info_thread and self.info_thread.isRunning():
            self.info_thread.stop()
            self.info_thread.wait()
        
        if not self.returning_to_hub:
            # Only pause downloads if actually closing the app, not returning to hub
            if self.download_thread and self.download_thread.isRunning():
                print("Closing window and stopping download")
                self.download_thread.stop(pause=True)  # Explicitly pause when closing
                self.download_thread.wait()
        else:
            print("Returning to hub - keeping download active in background")
        
        event.accept()
