from PyQt5.QtCore import QObject, pyqtSignal, QMutex, QMutexLocker
import time
import uuid
import json
import os
import sys

class DownloadInfo:
    def __init__(self, source, title, thumbnail_path=None):
        self.id = str(uuid.uuid4())
        self.source = source  # 'youtube', 'tiktok', 'facebook', etc.
        self.title = title
        self.thumbnail_path = thumbnail_path
        self.progress = 0
        self.speed = "0 KB/s"
        self.downloaded = "0 MB"
        self.total_size = "0 MB"
        self.remaining_time = "--"
        self.status = "running"  # running, paused, completed, error
        self.error_message = ""
        self.output_file = ""
        self.start_time = time.time()
        self.timestamp = time.time()
    
    def update(self, progress=None, speed=None, downloaded=None, 
               total_size=None, remaining_time=None, status=None, 
               error_message=None, output_file=None):
        if progress is not None: self.progress = progress
        if speed is not None: self.speed = speed
        if downloaded is not None: self.downloaded = downloaded
        if total_size is not None: self.total_size = total_size
        if remaining_time is not None: self.remaining_time = remaining_time
        if status is not None: self.status = status
        if error_message is not None: self.error_message = error_message
        if output_file is not None: self.output_file = output_file
        self.timestamp = time.time()  # Update timestamp when the download is updated
    
    def to_dict(self):
        """Convert DownloadInfo to dictionary for serialization"""
        return {
            'id': self.id,
            'source': self.source,
            'title': self.title,
            'thumbnail_path': self.thumbnail_path,
            'progress': self.progress,
            'status': self.status,
            'output_file': self.output_file,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create DownloadInfo from dictionary"""
        download_info = cls(data['source'], data['title'], data.get('thumbnail_path'))
        download_info.id = data['id']
        download_info.progress = data['progress']
        download_info.status = data['status']
        download_info.output_file = data.get('output_file', '')
        download_info.timestamp = data.get('timestamp', time.time())
        return download_info


class DownloadManager(QObject):
    download_updated = pyqtSignal(str)  # Emits download_id when a download is updated
    download_completed = pyqtSignal(str, str)  # Emits download_id, output_file
    download_error = pyqtSignal(str, str)  # Emits download_id, error_message
    download_removed = pyqtSignal(str)  # Emits download_id when a download is removed
    
    _instance = None
    _mutex = QMutex()
    
    @staticmethod
    def get_instance():
        if DownloadManager._instance is None:
            with QMutexLocker(DownloadManager._mutex):
                if DownloadManager._instance is None:
                    DownloadManager._instance = DownloadManager()
        return DownloadManager._instance
    
    def __init__(self):
        super().__init__()
        self.downloads = {}  # Map of download_id to DownloadInfo
        self.load_downloads()  # Load downloads when initializing
    
    def add_download(self, source, title, thumbnail_path=None):
        download_info = DownloadInfo(source, title, thumbnail_path)
        self.downloads[download_info.id] = download_info
        self.save_downloads()  # Save downloads after adding a new one
        return download_info.id
    
    def update_download(self, download_id, **kwargs):
        if download_id in self.downloads:
            self.downloads[download_id].update(**kwargs)
            self.download_updated.emit(download_id)
            
            # Check for completion or error
            status = kwargs.get('status')
            if status == 'completed':
                self.download_completed.emit(download_id, self.downloads[download_id].output_file)
                self.save_downloads()  # Save downloads after completion
            elif status == 'error':
                self.download_error.emit(download_id, kwargs.get('error_message', ''))
                self.save_downloads()  # Save downloads after error
    
    def remove_download(self, download_id):
        """Remove a download from the list with improved error handling"""
        try:
            if not download_id:
                print("Warning: Attempted to remove download with empty ID")
                return False
                
            # Double-check the download exists
            if download_id in self.downloads:
                print(f"Removing download: {download_id}")
                
                # Get info before deletion for logging
                download_info = self.downloads[download_id]
                output_file = download_info.output_file if hasattr(download_info, 'output_file') else None
                
                # Remove download from dictionary
                del self.downloads[download_id]
                
                # Emit signal after successful removal
                try:
                    self.download_removed.emit(download_id)
                    print(f"Emitted download_removed signal for: {download_id}")
                except Exception as signal_error:
                    print(f"Error emitting download_removed signal: {str(signal_error)}")
                
                # Save downloads after removal
                self.save_downloads()
                
                # Return summary
                return {
                    'success': True,
                    'id': download_id,
                    'file': output_file,
                    'file_exists': output_file and os.path.exists(output_file)
                }
                
            print(f"Warning: Download ID not found: {download_id}")
            return False
        except Exception as e:
            print(f"Error removing download: {str(e)}")
            return False
    
    def get_download(self, download_id):
        """Get a download by ID with improved error handling"""
        if not download_id:
            return None
            
        return self.downloads.get(download_id)
    
    def get_all_downloads(self):
        """Get all downloads as a list with validation"""
        try:
            valid_downloads = []
            for download_id, download_info in self.downloads.items():
                if download_id and download_info:
                    valid_downloads.append(download_info)
            return valid_downloads
        except Exception as e:
            print(f"Error getting downloads: {str(e)}")
            return []
    
    def get_active_downloads(self):
        return [info for info in self.downloads.values() 
                if info.status == 'running' or info.status == 'paused']
    
    def get_completed_downloads(self):
        return [info for info in self.downloads.values() 
                if info.status == 'completed']
    
    def get_failed_downloads(self):
        return [info for info in self.downloads.values() 
                if info.status == 'error']
    
    def get_data_dir(self):
        """Get the directory for saving persistent data"""
        try:
            # Get the application's directory - fixing the path to ensure it exists
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0])))
            data_dir = os.path.join(app_dir, "data")
            
            # Create directory if it doesn't exist
            os.makedirs(data_dir, exist_ok=True)
            
            # Verify it's writable by testing
            test_file = os.path.join(data_dir, ".test_write")
            try:
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
            except Exception as e:
                print(f"Warning: Data directory is not writable: {str(e)}")
                # Fall back to temp directory
                import tempfile
                data_dir = tempfile.gettempdir()
                print(f"Using temp directory instead: {data_dir}")
            
            return data_dir
        except Exception as e:
            print(f"Error getting data directory: {str(e)}")
            # Fall back to temp directory
            import tempfile
            return tempfile.gettempdir()
    
    def get_downloads_file_path(self):
        """Get the path to the downloads data file"""
        return os.path.join(self.get_data_dir(), "downloads.json")
    
    def save_downloads(self):
        """Save downloads to a JSON file"""
        try:
            downloads_data = []
            for download_id, download_info in self.downloads.items():
                # Only save completed or failed downloads
                if download_info.status in ['completed', 'error']:
                    # Check if output file exists for completed downloads
                    if download_info.status == 'completed' and download_info.output_file:
                        if not os.path.exists(download_info.output_file):
                            # Skip if file doesn't exist
                            continue
                    downloads_data.append(download_info.to_dict())
            
            # Sort by timestamp (newest first)
            downloads_data.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
            
            with open(self.get_downloads_file_path(), 'w', encoding='utf-8') as f:
                json.dump(downloads_data, f, ensure_ascii=False, indent=2)
            
            print(f"Downloads saved to {self.get_downloads_file_path()}")
        except Exception as e:
            print(f"Error saving downloads: {str(e)}")
    
    def load_downloads(self):
        """Load downloads from a JSON file"""
        try:
            file_path = self.get_downloads_file_path()
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    downloads_data = json.load(f)
                
                for data in downloads_data:
                    # Skip if output file doesn't exist for completed downloads
                    if data['status'] == 'completed' and data.get('output_file') and not os.path.exists(data.get('output_file')):
                        continue
                    
                    # Skip if thumbnail doesn't exist
                    if data.get('thumbnail_path') and not os.path.exists(data.get('thumbnail_path')):
                        data['thumbnail_path'] = None
                    
                    download_info = DownloadInfo.from_dict(data)
                    self.downloads[download_info.id] = download_info
                
                print(f"Loaded {len(self.downloads)} downloads")
        except Exception as e:
            print(f"Error loading downloads: {str(e)}")