from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFileDialog, QProgressBar, QStatusBar, QComboBox,
                             QMessageBox, QGroupBox, QFrame)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
import os
import time
import urllib.parse
import requests
import sys
import subprocess
import re
import json
from io import BytesIO
from utils.helpers import clean_filename, format_size, format_time
from utils import compat  # Import the compatibility module
import yt_dlp
from utils.download_manager import DownloadManager  # Thêm import DownloadManager
from utils.config_manager import ConfigManager  # Add this import


class FacebookInfoThread(QThread):
    info_ready = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url
        self.should_stop = False

    def run(self):
        try:
            self.progress.emit("Kiểm tra thư viện yt-dlp...")
            
            self.progress.emit("Đang tải thông tin video từ Facebook...")
            
            # Enhanced options for Facebook extraction
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 30,
                'nocheckcertificate': True,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                'referer': 'https://www.facebook.com/'
            }
            
            # Try standard extraction first
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    if self.should_stop:
                        return
                    
                    self.progress.emit("Trích xuất thông tin chi tiết...")
                    info_dict = ydl.extract_info(self.url, download=False)
                    
                    if info_dict:
                        # Generate format list
                        formats = []
                        
                        # Add best quality option
                        formats.append({
                            'format_id': 'best',
                            'ext': 'mp4',
                            'display_name': 'Video chất lượng cao nhất',
                            'is_audio': False
                        })
                        
                        # Add audio option
                        formats.append({
                            'format_id': 'bestaudio',
                            'ext': 'mp3',
                            'display_name': 'Chỉ âm thanh (MP3)',
                            'is_audio': True
                        })
                        
                        # Add specific quality formats if available
                        for fmt in info_dict.get('formats', []):
                            if fmt.get('height') and fmt.get('format_id') != 'best':
                                height = fmt.get('height')
                                formats.append({
                                    'format_id': fmt['format_id'],
                                    'ext': fmt.get('ext', 'mp4'),
                                    'display_name': f"{height}p",
                                    'is_audio': False
                                })
                        
                        # Create video info structure
                        video_info = {
                            'title': info_dict.get('title', 'Facebook video'),
                            'uploader': info_dict.get('uploader', 'Unknown user'),
                            'duration': info_dict.get('duration', 0),
                            'thumbnail_url': info_dict.get('thumbnail', ''),
                            'formats': formats,
                            'default_format_index': 0
                        }
                        
                        self.info_ready.emit(video_info)
                        return
            except Exception as e:
                self.progress.emit(f"Phương pháp tiêu chuẩn thất bại, thử phương pháp thay thế: {str(e)}")
            
            # Direct method using requests as fallback
            self.try_direct_extraction()
                
        except Exception as e:
            self.error.emit(f"Lỗi: {str(e)}")
    
    def try_direct_extraction(self):
        """Try to extract video info directly from the Facebook page"""
        try:
            self.progress.emit("Đang thử phương pháp trích xuất trực tiếp...")
            
            # Get video ID from URL
            video_id = self.extract_facebook_id(self.url)
            if not video_id:
                self.error.emit("Không thể xác định ID video từ URL")
                return
                
            self.progress.emit(f"Đã tìm thấy ID video: {video_id}")
                
            # Define modern browser headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'cross-site',
                'Cache-Control': 'max-age=0',
            }
            
            self.progress.emit("Đang truy cập trang Facebook...")
            
            # Try multiple URL formats
            url_formats = [
                f"https://www.facebook.com/watch/?v={video_id}",
                f"https://www.facebook.com/watch/v/?v={video_id}",
                f"https://www.facebook.com/video.php?v={video_id}",
                f"https://www.facebook.com/reel/{video_id}",
                self.url  # original URL as last resort
            ]
            
            response = None
            for url in url_formats:
                try:
                    self.progress.emit(f"Thử truy cập: {url}")
                    response = requests.get(url, headers=headers, timeout=15)
                    if response.status_code == 200:
                        self.progress.emit(f"Truy cập thành công: {url}")
                        break
                except Exception as e:
                    self.progress.emit(f"Lỗi truy cập {url}: {str(e)}")
            
            if not response or response.status_code != 200:
                self.error.emit(f"Không thể truy cập trang Facebook (Status code: {response.status_code if response else 'Unknown'})")
                return
                
            self.progress.emit("Đang tìm kiếm thông tin video...")
                
            # Look for video data in the page content
            page_content = response.text
            
            # Try multiple pattern matching approaches
            video_url = None
            
            # Method 1: Look for HD and SD sources
            self.progress.emit("Tìm kiếm HD/SD sources...")
            hd_src_match = re.search(r'"hd_src":"(https:\\\/\\\/[^"]*)"', page_content)
            sd_src_match = re.search(r'"sd_src":"(https:\\\/\\\/[^"]*)"', page_content)
            
            if hd_src_match:
                video_url = hd_src_match.group(1).replace('\\/', '/')
                self.progress.emit("Tìm thấy HD source")
            elif sd_src_match:
                video_url = sd_src_match.group(1).replace('\\/', '/')
                self.progress.emit("Tìm thấy SD source")
            
            # Method 2: Look for video data in JSON structures
            if not video_url:
                self.progress.emit("Tìm kiếm trong cấu trúc JSON...")
                json_patterns = [
                    r'videoData"?:\s*{(?:[^{}]|{[^{}]*})*?}',
                    r'"videoData"?:\s*\[[^\]]*\]',
                    r'"media"?:\s*{(?:[^{}]|{[^{}]*})*?}',
                    r'"media"?:\s*\[[^\]]*\]',
                    r'"attachments"?:\s*\[[^\]]*\]',
                ]
                
                for pattern in json_patterns:
                    json_matches = re.finditer(pattern, page_content)
                    for match in json_matches:
                        json_str = match.group(0)
                        try:
                            # Look for URLs within this JSON structure
                            urls = re.findall(r'(https?://[^"\']+\.mp4[^"\']*)', json_str)
                            if urls:
                                video_url = urls[0].replace('\\/', '/')
                                self.progress.emit(f"Tìm thấy URL video trong JSON: {video_url[:50]}...")
                                break
                        except:
                            continue
                    
                    if video_url:
                        break
            
            # Method 3: Search for video source tags in HTML
            if not video_url:
                self.progress.emit("Tìm kiếm thẻ video trong HTML...")
                video_tags = re.findall(r'<video[^>]*>(.*?)</video>', page_content, re.DOTALL)
                for tag in video_tags:
                    source_match = re.search(r'src=["\'](https?://[^\'"]+)[\'"]', tag)
                    if source_match:
                        video_url = source_match.group(1)
                        self.progress.emit(f"Tìm thấy URL video trong thẻ video: {video_url[:50]}...")
                        break
            
            # Method 4: Generic URL pattern matching
            if not video_url:
                self.progress.emit("Tìm kiếm URL MP4 bất kỳ...")
                url_patterns = [
                    r'(https?://[^"\'>\s]+\.mp4[^"\'>\s]*)',
                    r'(https?://video[\.\-][^"\'>\s]+)',
                    r'(https?://[^"\'>\s]*fbcdn[^"\'>\s]*)',
                    r'(https?://[^"\'>\s]*fbpx[^"\'>\s]*)'
                ]
                
                for pattern in url_patterns:
                    url_matches = re.findall(pattern, page_content)
                    if url_matches:
                        video_url = url_matches[0].replace('\\/', '/')
                        self.progress.emit(f"Tìm thấy URL MP4: {video_url[:50]}...")
                        break
            
            # Try to find title and author
            self.progress.emit("Tìm kiếm thông tin tiêu đề và tác giả...")
            title = "Facebook Video"
            uploader = "Unknown"
            thumbnail = None
            
            # Title
            title_patterns = [
                r'<meta property="og:title" content="([^"]+)"',
                r'<title>(.*?)</title>',
                r'"name":"([^"]+)"'
            ]
            
            for pattern in title_patterns:
                title_match = re.search(pattern, page_content)
                if title_match:
                    title = title_match.group(1).replace(" | Facebook", "")
                    title = title.replace("Facebook Watch", "").strip()
                    if title:
                        break
            
            # Uploader
            uploader_patterns = [
                r'<meta property="og:site_name" content="([^"]+)"',
                r'"ownerName":"([^"]+)"',
                r'"publisher_name":"([^"]+)"',
                r'"publisher":\{"name":"([^"]+)"'
            ]
            
            for pattern in uploader_patterns:
                uploader_match = re.search(pattern, page_content)
                if uploader_match:
                    uploader = uploader_match.group(1)
                    break
            
            # Thumbnail
            thumbnail_patterns = [
                r'<meta property="og:image" content="([^"]+)"',
                r'"thumbnailUrl":"(https:\\\/\\\/[^"]*)"',
                r'"thumbnailImage":{"uri":"([^"]+)"',
                r'"image":{"uri":"([^"]+)"'
            ]
            
            for pattern in thumbnail_patterns:
                thumbnail_match = re.search(pattern, page_content)
                if thumbnail_match:
                    thumbnail = thumbnail_match.group(1).replace('\\/', '/')
                    break
            
            if not video_url:
                self.error.emit("Không thể tìm URL video trong trang")
                return
            else:
                self.progress.emit(f"Đã tìm thấy URL video: {video_url[:50]}...")
                
            # Create formats list
            formats = [
                {
                    'format_id': 'best',
                    'ext': 'mp4',
                    'display_name': 'Video chất lượng cao nhất',
                    'is_audio': False
                },
                {
                    'format_id': 'bestaudio',
                    'ext': 'mp3',
                    'display_name': 'Chỉ âm thanh (MP3)',
                    'is_audio': True
                }
            ]
            
            # Create video info
            video_info = {
                'title': title,
                'uploader': uploader,
                'duration': 0,  # Unknown from direct extraction
                'thumbnail_url': thumbnail,
                'formats': formats,
                'default_format_index': 0,
                'direct_url': video_url  # Store direct URL for download
            }
            
            self.progress.emit("Trích xuất thông tin video thành công!")
            self.info_ready.emit(video_info)
            
        except Exception as e:
            self.error.emit(f"Lỗi khi trích xuất trực tiếp: {str(e)}")
    
    def extract_facebook_id(self, url):
        """Extract Facebook video ID from URL"""
        # Pattern 1: videos/12345678
        pattern1 = r'\/videos\/(\d+)'
        match = re.search(pattern1, url)
        if match:
            return match.group(1)
            
        # Pattern 2: v=12345678 or ?v=12345678
        pattern2 = r'[?&]v=(\d+)'
        match = re.search(pattern2, url)
        if match:
            return match.group(1)
            
        # Pattern 3: watch/?v=12345678
        pattern3 = r'watch\/?\?v=(\d+)'
        match = re.search(pattern3, url)
        if match:
            return match.group(1)
            
        # Pattern 4: Just a number in the URL (for URLs like the one in the error)
        pattern4 = r'\/(\d{15,})'
        match = re.search(pattern4, url)
        if match:
            return match.group(1)
            
        # Pattern 5: idorvanity parameter (like in the error URL)
        pattern5 = r'[?&]idorvanity=(\d+)'
        match = re.search(pattern5, url)
        if match:
            return match.group(1)
            
        # Pattern 6: Reel URLs
        pattern6 = r'\/reel\/(\d+)'
        match = re.search(pattern6, url)
        if match:
            return match.group(1)
            
        return None
    
    def stop(self):
        self.should_stop = True


class FacebookDownloadThread(QThread):
    progress = pyqtSignal(int, str, str, str, str)  # phần trăm, tốc độ, đã tải, thời gian còn lại, tổng kích thước
    finished = pyqtSignal(str)  # file đầu ra
    error = pyqtSignal(str)  # thông báo lỗi
    
    def __init__(self, url, format_id, output_path, direct_url=None):
        super().__init__()
        self.url = url
        self.format_id = format_id
        self.output_path = output_path
        self.direct_url = direct_url  # URL trực tiếp (nếu có)
        self.should_stop = False
        self.download_manager = DownloadManager.get_instance()
        self.download_id = None
        
    def run(self):
        try:
            # Tạo ID tải xuống và thêm vào download manager
            self.download_id = self.download_manager.add_download(
                source='facebook',
                title=self.url,  # Ban đầu chỉ có URL, cập nhật title sau
                thumbnail_path=None
            )
            
            # Nếu có direct_url, ưu tiên sử dụng
            if self.direct_url and self.format_id == 'best':
                self.download_with_direct_url()
                return
                
            # Thiết lập các tùy chọn cho yt-dlp
            ydl_opts = {
                'format': self.format_id,
                'outtmpl': os.path.join(self.output_path, '%(title)s.%(ext)s'),
                'noplaylist': True,
                'progress_hooks': [self.progress_hook],
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': False,
                'nocheckcertificate': True,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                'referer': 'https://www.facebook.com/',
                'socket_timeout': 30
            }
            
            # Nếu chọn tải audio
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
            elif self.format_id == 'best':
                # Ensure audio is included in best format downloads
                ydl_opts['format'] = 'bestvideo+bestaudio/best'
            
            # Tạo logger để bắt thông tin file đã tải
            class MyLogger:
                def __init__(self):
                    self.downloaded_files = []
                
                def debug(self, msg):
                    # Bắt tên file đích
                    if 'Destination:' in msg:
                        try:
                            filename = msg.split('Destination: ')[1].strip()
                            self.downloaded_files.append(filename)
                            print(f"Debug: Found file path: {filename}")
                        except Exception as e:
                            print(f"Error parsing filename: {str(e)}")
                
                def warning(self, msg):
                    pass
                
                def error(self, msg):
                    print(f"Error: {msg}")
            
            logger = MyLogger()
            ydl_opts['logger'] = logger
            
            # Tải xuống video
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if self.direct_url:
                    # Nếu có direct_url, thử lấy thông tin video từ URL gốc
                    # và tải xuống từ direct_url
                    info_dict = ydl.extract_info(self.url, download=False)
                    
                    # Ghi đè URL trong info_dict để tải từ direct_url
                    if info_dict:
                        info_dict['url'] = self.direct_url
                        ydl.process_ie_result(info_dict, download=True)
                else:
                    # Nếu không có direct_url, tải xuống bình thường
                    info_dict = ydl.extract_info(self.url, download=True)
                
                # Cập nhật thông tin vào download manager
                if info_dict and 'title' in info_dict:
                    download_info = self.download_manager.downloads[self.download_id]
                    download_info.title = info_dict['title']
                    
                    # Save thumbnail
                    if 'thumbnail' in info_dict:
                        try:
                            thumbnail_url = info_dict['thumbnail']
                            # Get the application's directory
                            app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
                            # Create thumbnails directory if it doesn't exist
                            thumbnails_dir = os.path.join(app_dir, "thumbnails")
                            os.makedirs(thumbnails_dir, exist_ok=True)
                            
                            thumbnail_path = os.path.join(thumbnails_dir, f"fb_{int(time.time())}_{clean_filename(info_dict['title'])}_thumbnail.jpg")
                            
                            response = requests.get(thumbnail_url)
                            if response.status_code == 200:
                                with open(thumbnail_path, 'wb') as f:
                                    f.write(response.content)
                                download_info.thumbnail_path = thumbnail_path
                        except Exception as e:
                            print(f"Không thể lưu thumbnail: {str(e)}")
            
            if not self.should_stop:
                # Kiểm tra xem có tải xuống thành công không
                if logger.downloaded_files:
                    downloaded_file = logger.downloaded_files[-1]
                    
                    # Cập nhật thông tin trong download manager
                    self.download_manager.update_download(
                        self.download_id,
                        status='completed',
                        progress=100,
                        output_file=downloaded_file
                    )
                    
                    self.finished.emit(downloaded_file)
                    
                    # Set the current timestamp for the downloaded file
                    self.set_current_timestamp(downloaded_file)
                else:
                    # Thử tìm file dựa trên thời gian tạo
                    files = os.listdir(self.output_path)
                    if files:
                        # Sắp xếp theo thời gian tạo, mới nhất đầu tiên
                        files.sort(key=lambda x: os.path.getctime(os.path.join(self.output_path, x)), reverse=True)
                        newest_file = os.path.join(self.output_path, files[0])
                        
                        self.download_manager.update_download(
                            self.download_id,
                            status='completed',
                            progress=100,
                            output_file=newest_file
                        )
                        
                        self.finished.emit(newest_file)
                        
                        # Set the current timestamp for the downloaded file
                        self.set_current_timestamp(newest_file)
                    else:
                        raise Exception("Không tìm thấy file đã tải xuống")
                        
        except Exception as e:
            if not self.should_stop:
                error_message = str(e)
                self.download_manager.update_download(
                    self.download_id,
                    status='error',
                    error_message=error_message
                )
                self.error.emit(error_message)
    
    def download_with_direct_url(self):
        """Tải xuống video từ direct URL nếu có"""
        try:
            if not self.direct_url:
                raise Exception("Không có URL trực tiếp của video")
                
            self.progress.emit(10, "-- KB/s", "Đang chuẩn bị...", "--", "--")
            
            # Tạo tên file từ URL hoặc timestamp
            timestamp = int(time.time())
            url_filename = clean_filename(os.path.basename(self.url))
            if not url_filename or len(url_filename) < 5:
                filename = f"facebook_video_{timestamp}.mp4"
            else:
                filename = f"{url_filename}_{timestamp}.mp4"
            
            output_path = os.path.join(self.output_path, filename)
            
            # Modify headers to increase chances of getting video with audio
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                'Referer': 'https://www.facebook.com/',
                'Range': 'bytes=0-',  # Request full content
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Connection': 'keep-alive',
            }
            
            self.progress.emit(15, "-- KB/s", "Khởi tạo kết nối...", "--", "--")
            
            response = requests.get(self.direct_url, stream=True, headers=headers, verify=False)
            
            if response.status_code != 200:
                raise Exception(f"Lỗi khi tải xuống: HTTP Status {response.status_code}")
                
            # Lấy kích thước file nếu có
            file_size = int(response.headers.get('content-length', 0))
            
            if file_size == 0:
                self.progress.emit(20, "-- KB/s", "Không thể xác định kích thước", "--", "--")
            
            # Format kích thước
            if file_size < 1024 * 1024:
                total_size_str = f"{file_size/1024:.1f} KB"
            else:
                total_size_str = f"{file_size/(1024*1024):.1f} MB"
            
            # Tải xuống và theo dõi tiến trình
            start_time = time.time()
            downloaded = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.should_stop:
                        f.close()
                        os.remove(output_path)
                        self.download_manager.update_download(
                            self.download_id,
                            status='paused'
                        )
                        return
                        
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Tính toán phần trăm
                        if file_size > 0:
                            percent = int((downloaded / file_size) * 100)
                        else:
                            percent = 50  # Không thể xác định chính xác
                        
                        # Tính toán tốc độ
                        elapsed_time = time.time() - start_time
                        if elapsed_time > 0:
                            speed = downloaded / elapsed_time
                            if speed < 1024:
                                speed_str = f"{speed:.1f} B/s"
                            elif speed < 1024 * 1024:
                                speed_str = f"{speed/1024:.1f} KB/s"
                            else:
                                speed_str = f"{speed/(1024*1024):.1f} MB/s"
                        else:
                            speed_str = "-- KB/s"
                            
                        # Format kích thước đã tải
                        if downloaded < 1024 * 1024:
                            downloaded_str = f"{downloaded/1024:.1f} KB"
                        else:
                            downloaded_str = f"{downloaded/(1024*1024):.1f} MB"
                        
                        # Tính toán thời gian còn lại
                        if speed > 0 and file_size > 0:
                            eta = (file_size - downloaded) / speed
                            if eta < 60:
                                eta_str = f"{int(eta)}s"
                            elif eta < 3600:
                                eta_str = f"{int(eta//60)}m {int(eta%60)}s"
                            else:
                                eta_str = f"{int(eta//3600)}h {int((eta%3600)//60)}m"
                        else:
                            eta_str = "--"
                            
                        # Cập nhật tiến trình
                        self.progress.emit(percent, speed_str, downloaded_str, eta_str, total_size_str)
                        
                        # Cập nhật vào download manager
                        self.download_manager.update_download(
                            self.download_id,
                            progress=percent,
                            speed=speed_str,
                            downloaded=downloaded_str,
                            total_size=total_size_str,
                            remaining_time=eta_str
                        )
            
            # Đã tải xuống thành công
            self.download_manager.update_download(
                self.download_id,
                status='completed',
                progress=100,
                output_file=output_path
            )
            
            self.finished.emit(output_path)
            
            # Set the current timestamp for the downloaded file
            self.set_current_timestamp(output_path)
            
        except Exception as e:
            if not self.should_stop:
                error_message = f"Lỗi khi tải trực tiếp: {str(e)}"
                self.download_manager.update_download(
                    self.download_id,
                    status='error',
                    error_message=error_message
                )
                self.error.emit(error_message)
    
    def progress_hook(self, d):
        if self.should_stop:
            raise Exception("Download cancelled")
            
        if d['status'] == 'downloading':
            # Tính toán tiến trình
            total_bytes = d.get('total_bytes')
            total_bytes_estimate = d.get('total_bytes_estimate')
            
            total_size = total_bytes or total_bytes_estimate or 0
            downloaded_bytes = d.get('downloaded_bytes', 0)
            
            if total_size > 0:
                percent = int((downloaded_bytes / total_size) * 100)
            else:
                percent = 0
                
            # Format tốc độ
            speed = d.get('speed', 0) or 0
            if speed < 1024:
                speed_str = f"{speed:.1f} B/s"
            elif speed < 1024 * 1024:
                speed_str = f"{speed/1024:.1f} KB/s"
            else:
                speed_str = f"{speed/(1024*1024):.1f} MB/s"
            
            # Format kích thước đã tải
            if downloaded_bytes < 1024 * 1024:
                downloaded_str = f"{downloaded_bytes/1024:.1f} KB"
            else:
                downloaded_str = f"{downloaded_bytes/(1024*1024):.1f} MB"
            
            # Format tổng kích thước
            if total_size < 1024 * 1024:
                total_size_str = f"{total_size/1024:.1f} KB"
            else:
                total_size_str = f"{total_size/(1024*1024):.1f} MB"
                
            # Format thời gian còn lại
            eta = d.get('eta', 0) or 0
            if eta < 60:
                eta_str = f"{eta}s"
            elif eta < 3600:
                eta_str = f"{eta//60}m {eta%60}s"
            else:
                eta_str = f"{eta//3600}h {(eta%3600)//60}m"
            
            # Cập nhật giao diện và download manager
            self.progress.emit(percent, speed_str, downloaded_str, eta_str, total_size_str)
            
            self.download_manager.update_download(
                self.download_id,
                progress=percent,
                speed=speed_str,
                downloaded=downloaded_str,
                total_size=total_size_str,
                remaining_time=eta_str
            )
    
    def set_current_timestamp(self, file_path):
        """Đặt thời gian tạo file là thời gian hiện tại"""
        try:
            current_time = time.time()
            os.utime(file_path, (current_time, current_time))
            print(f"Set timestamp of {file_path} to current time")
        except Exception as e:
            print(f"Error setting timestamp: {str(e)}")
    
    def stop(self, pause=True):
        """Stop the download thread, optionally setting status to paused"""
        self.should_stop = True
        # Only change status if specifically requesting to pause
        if pause:
            self.download_manager.update_download(
                self.download_id,
                status='paused'
            )


class FacebookDownloaderWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KHyTool - Facebook Downloader")
        self.setMinimumSize(900, 650)
        self.showMaximized()
        
        # Use ConfigManager for output path
        self.config_manager = ConfigManager.get_instance()
        self.output_path = self.config_manager.get_download_dir()
        
        self.info_thread = None
        self.download_thread = None
        self.returning_to_hub = False  # Add flag to track return to hub action
        self.initUI()
        self.setStyleSheet("""
            QMainWindow {
                background-color: #FFFFFF;
            }
            QLabel {
                color: #121212;
                font-size: 14px;
            }
            QLabel#header {
                font-size: 32px;
                font-weight: bold;
                color: #1877F2;
            }
            QLabel#info {
                font-weight: bold;
                color: #121212;
                font-size: 16px;
            }
            QPushButton {
                background-color: #1877F2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #166FE5;
            }
            QPushButton:pressed {
                background-color: #0E5FCC;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
            QPushButton#secondary {
                background-color: #42B72A;
                color: white;
            }
            QPushButton#secondary:hover {
                background-color: #36A420;
            }
            QPushButton#secondary:pressed {
                background-color: #2B9217;
            }
            QPushButton#cancel {
                background-color: #E4E6EB;
                color: #050505;
            }
            QPushButton#cancel:hover {
                background-color: #D8DADF;
            }
            QPushButton#cancel:pressed {
                background-color: #CED0D4;
            }
            QLineEdit {
                border: 1px solid #DDDFE2;
                border-radius: 6px;
                padding: 12px;
                font-size: 16px;
            }
            QLineEdit:focus {
                border: 2px solid #1877F2;
            }
            QProgressBar {
                border: 1px solid #DDDFE2;
                border-radius: 6px;
                text-align: center;
                height: 24px;
                font-weight: bold;
                font-size: 14px;
            }
            QProgressBar::chunk {
                background-color: #1877F2;
                border-radius: 5px;
            }
            QComboBox {
                border: 1px solid #DDDFE2;
                border-radius: 6px;
                padding: 10px;
                min-width: 250px;
                font-size: 14px;
            }
            QComboBox:hover {
                border: 1px solid #CCD0D5;
            }
            QComboBox:focus {
                border: 2px solid #1877F2;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #DDDFE2;
                border-radius: 10px;
                margin-top: 14px;
                padding: 15px;
                font-size: 16px;
                background-color: #fafafa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
                color: #1877F2;
                background-color: #ffffff;
                font-size: 18px;
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
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(25)

        # Header với thiết kế tối giản, chuyên nghiệp
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(10, 5, 10, 5)
        
        header_label = QLabel("Facebook Downloader")
        header_label.setObjectName("header")
        header_label.setAlignment(Qt.AlignCenter)
        # Tạo hiệu ứng viền nổi với màu Facebook
        header_label.setStyleSheet("""
            font-size: 36px;
            font-weight: bold;
            color: #1877F2;
            border-bottom: 3px solid #1877F2;
            padding-bottom: 5px;
        """)
        header_layout.addWidget(header_label, 1)
        
        layout.addWidget(header_widget)

        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #1877F2; min-height: 2px;")
        layout.addWidget(separator)

        # URL Input với thiết kế chuyên nghiệp
        input_group = QGroupBox("URL Video")
        input_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #1877F2;
                border-radius: 12px;
                margin-top: 16px;
                background-color: #ffffff;
                padding: 18px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
                color: #1877F2;
                background-color: #ffffff;
                font-size: 18px;
            }
        """)
        input_layout = QVBoxLayout(input_group)
        input_layout.setSpacing(15)

        link_layout = QHBoxLayout()
        self.link_input = QLineEdit()
        self.link_input.setPlaceholderText("Nhập link Facebook...")
        self.link_input.setMinimumHeight(50)
        
        fetch_button = QPushButton("Lấy thông tin")
        fetch_button.setObjectName("secondary")
        fetch_button.setMinimumHeight(50)
        fetch_button.setMinimumWidth(150)
        fetch_button.clicked.connect(self.fetch_video_info)
        
        link_layout.addWidget(self.link_input)
        link_layout.addWidget(fetch_button)
        input_layout.addLayout(link_layout)
        
        # Helper text
        helper_label = QLabel("Ví dụ: https://www.facebook.com/username/videos/123456789")
        helper_label.setStyleSheet("color: #777777; font-size: 14px; font-style: italic;")
        input_layout.addWidget(helper_label)
        
        layout.addWidget(input_group)

        # Video Info Panel - cải thiện bố cục 3 cột
        info_group = QGroupBox("Thông tin Video")
        info_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #1877F2;
                border-radius: 12px;
                margin-top: 16px;
                background-color: #ffffff;
                padding: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
                color: #1877F2;
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
                border: 2px solid #1877F2;
                border-radius: 10px;
                padding: 2px;
            }
        """)
        thumbnail_layout = QVBoxLayout(thumbnail_frame)
        thumbnail_layout.setContentsMargins(0, 0, 0, 0)
        
        # Chuẩn hóa kích thước thumbnail
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
        
        # Title với style mới
        self.title_label = QLabel("Tiêu đề: ")
        self.title_label.setObjectName("info")
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #333333;
            padding: 8px;
            background-color: #f0f0f0;
            border-left: 4px solid #1877F2;
            min-height: 20px;
        """)
        self.title_label.setMinimumHeight(50)
        details_layout.addWidget(self.title_label)
        
        # Author/Publisher
        self.publisher_label = QLabel("Tác giả: ")
        self.publisher_label.setObjectName("info")
        self.publisher_label.setWordWrap(True)
        self.publisher_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #333333;
            padding: 8px;
            background-color: #f0f0f0;
            border-left: 4px solid #42B72A;
            min-height: 20px;
        """)
        self.publisher_label.setMinimumHeight(40)
        details_layout.addWidget(self.publisher_label)
        
        # Duration
        self.duration_label = QLabel("Thời lượng: ")
        self.duration_label.setObjectName("info")
        self.duration_label.setWordWrap(True)
        self.duration_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #333333;
            padding: 8px;
            background-color: #f0f0f0;
            border-left: 4px solid #F02849;
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
        quality_label.setStyleSheet("font-weight: bold; color: #4267B2; font-size: 15px;")
        quality_layout.addWidget(quality_label)
        
        # Format selection
        self.format_combo = QComboBox()
        self.format_combo.setMinimumHeight(45)
        self.format_combo.setMinimumWidth(200)
        self.format_combo.setFont(QFont("Arial", 14))
        self.format_combo.setPlaceholderText("Chọn chất lượng")
        self.format_combo.setEnabled(False)  # Disabled mặc định
        self.format_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #D3D3D3;
                border-radius: 6px;
                padding: 10px;
                font-size: 14px;
                background-color: #f8f8f8;
                border-left: 4px solid #4267B2;
                color: #333333;
            }
            QComboBox:hover:enabled {
                border: 1px solid #A0A0A0;
            }
            QComboBox:focus {
                border: 2px solid #1877F2;
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

        # Output Path Selection
        path_group = QGroupBox("Đường dẫn lưu file")
        path_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #DDDFE2;
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
        
        self.path_label = QLabel(f"Đường dẫn tải về: {self.output_path}")
        self.path_label.setFont(QFont("Arial", 14))
        self.path_label.setStyleSheet("background-color: #f5f5f5; padding: 10px; border-radius: 6px;")
        
        path_button = QPushButton("Chọn thư mục")
        path_button.setObjectName("secondary")
        path_button.setMinimumHeight(45)
        path_button.setMinimumWidth(150)
        path_button.setFont(QFont("Arial", 14))
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
                background-color: #1877F2;
                color: white;
                border-radius: 8px;
                padding: 15px 30px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #166FE5;
            }
            QPushButton:pressed {
                background-color: #0E5FCC;
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
        
        # Khu vực thông tin không dùng icon
        progress_info_frame = QFrame()
        progress_info_frame.setStyleSheet("background-color: #f5f5f5; border-radius: 8px; padding: 15px;")
        progress_info_layout = QHBoxLayout(progress_info_frame)
        progress_info_layout.setSpacing(30)
        
        # Thông tin tốc độ
        speed_container = QWidget()
        speed_container_layout = QVBoxLayout(speed_container)
        speed_container_layout.setContentsMargins(0, 0, 0, 0)
        
        speed_header = QLabel("TỐC ĐỘ")
        speed_header.setAlignment(Qt.AlignCenter)
        speed_header.setStyleSheet("font-weight: bold; color: #2196F3; font-size: 14px;")
        speed_container_layout.addWidget(speed_header)
        
        self.speed_label = QLabel("-- KB/s")
        self.speed_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.speed_label.setAlignment(Qt.AlignCenter)
        self.speed_label.setStyleSheet("color: #2196F3;")
        speed_container_layout.addWidget(self.speed_label)
        
        progress_info_layout.addWidget(speed_container, 1)
        
        # Thông tin tiến độ
        progress_container = QWidget()
        progress_container_layout = QVBoxLayout(progress_container)
        progress_container_layout.setContentsMargins(0, 0, 0, 0)
        
        progress_header = QLabel("KÍCH THƯỚC")
        progress_header.setAlignment(Qt.AlignCenter)
        progress_header.setStyleSheet("font-weight: bold; color: #4CAF50; font-size: 14px;")
        progress_container_layout.addWidget(progress_header)
        
        self.downloaded_label = QLabel("-- / --")
        self.downloaded_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.downloaded_label.setAlignment(Qt.AlignCenter)
        self.downloaded_label.setStyleSheet("color: #4CAF50;")
        progress_container_layout.addWidget(self.downloaded_label)
        
        progress_info_layout.addWidget(progress_container, 1)
        
        # Thông tin thời gian
        time_container = QWidget()
        time_container_layout = QVBoxLayout(time_container)
        time_container_layout.setContentsMargins(0, 0, 0, 0)
        
        time_header = QLabel("THỜI GIAN CÒN LẠI")
        time_header.setAlignment(Qt.AlignCenter)
        time_header.setStyleSheet("font-weight: bold; color: #FF9800; font-size: 14px;")
        time_container_layout.addWidget(time_header)
        
        self.time_label = QLabel("--")
        self.time_label.setFont(QFont("Arial", 16, QFont.Bold))
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
        
        # Nút trở về - không dùng icon
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
        self.status_bar.setStyleSheet("QStatusBar { color: #121212; font-size: 14px; padding: 5px; }")
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Sẵn sàng tải video từ Facebook")

    def fetch_video_info(self):
        url = self.link_input.text().strip()
        if not url:
            self.status_bar.showMessage("Vui lòng nhập link Facebook")
            return
        
        # Kiểm tra xem URL có phải là Facebook không
        if "facebook.com" not in url and "fb.com" not in url and "fb.watch" not in url:
            QMessageBox.warning(self, "URL không hợp lệ", "Link không phải là Facebook. Vui lòng kiểm tra lại.")
            return
        
        # Hủy thread trước đó nếu đang chạy
        if self.info_thread and self.info_thread.isRunning():
            self.info_thread.stop()
            self.info_thread.wait(1000)
        
        # Cập nhật UI để hiển thị đang tải
        self.thumbnail_label.setText("Đang tải thông tin...")
        self.title_label.setText("Tiêu đề: Đang tải...")
        self.publisher_label.setText("Tác giả: Đang tải...")
        self.duration_label.setText("Thời lượng: Đang tải...")
        self.format_combo.clear()
        self.format_combo.setEnabled(False)  # Vô hiệu hóa combo box khi đang tải
        self.format_combo.setPlaceholderText("Đang tải danh sách chất lượng...")
        self.download_button.setEnabled(False)
        
        # Tạo và khởi chạy thread lấy thông tin
        self.info_thread = FacebookInfoThread(url)
        self.info_thread.info_ready.connect(self.update_video_info)
        self.info_thread.error.connect(self.handle_info_error)
        self.info_thread.progress.connect(self.update_fetch_progress)
        self.info_thread.start()
        
        self.status_bar.showMessage("Đang tải thông tin video...")

    def update_fetch_progress(self, message):
        self.status_bar.showMessage(message)

    def update_video_info(self, info):
        # Giới hạn độ dài tiêu đề để tránh lỗi hiển thị
        title = info['title']
        if len(title) > 80:  # Giới hạn độ dài hiển thị
            title = title[:77] + "..."
            
        # Update title
        self.title_label.setText(f"Tiêu đề: {title}")
        
        # Giới hạn độ dài tên tác giả
        uploader = info['uploader']
        if len(uploader) > 50:  # Giới hạn độ dài hiển thị
            uploader = uploader[:47] + "..."
            
        # Update author
        self.publisher_label.setText(f"Tác giả: {uploader}")
        
        # Update duration
        duration_str = format_time(info['duration'])
        self.duration_label.setText(f"Thời lượng: {duration_str}")
        
        # Lưu direct URL nếu có
        if 'direct_url' in info:
            self.direct_url = info['direct_url']
        else:
            self.direct_url = None
        
        # Tải và hiển thị thumbnail
        try:
            if info['thumbnail_url']:
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
        
        # Cập nhật combobox định dạng
        self.format_combo.clear()
        self.format_combo.setEnabled(True)  # Kích hoạt combo box
        self.format_combo.setPlaceholderText("Chọn chất lượng")
        for fmt in info['formats']:
            self.format_combo.addItem(fmt['display_name'], fmt['format_id'])
        
        # Đặt format mặc định
        if len(info['formats']) > 0:
            self.format_combo.setCurrentIndex(0)
        
        # Bật nút tải xuống
        self.download_button.setEnabled(True)
        self.status_bar.showMessage(f"Đã tải thông tin video: {info['title']}")

    def handle_info_error(self, error):
        self.status_bar.showMessage(f"Lỗi: {error}")
        self.thumbnail_label.setText(f"Lỗi: {error}")
        self.title_label.setText("Tiêu đề: --")
        self.publisher_label.setText("Trang/Người đăng: --")
        self.duration_label.setText("Thời lượng: --")
        self.download_button.setEnabled(False)
        QMessageBox.critical(self, "Lỗi", f"Không thể tải thông tin video: {error}")

    def select_output_path(self):
        path = QFileDialog.getExistingDirectory(self, "Chọn đường dẫn lưu video", self.output_path)
        if path:
            self.output_path = path
            self.path_label.setText(f"Đường dẫn tải về: {self.output_path}")
            # Save path to shared configuration
            self.config_manager.set_download_dir(path)

    def download_video(self):
        url = self.link_input.text().strip()
        format_id = self.format_combo.currentData()
        
        if not url:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập link Facebook")
            return
        
        if not format_id:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn định dạng tải xuống")
            return
        
        # Kiểm tra quyền ghi vào thư mục đầu ra
        try:
            test_file = os.path.join(self.output_path, ".test_write_permission")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi quyền truy cập", 
                f"Không thể ghi vào thư mục đầu ra: {self.output_path}\nLỗi: {str(e)}")
            return
        
        # Hủy thread tải xuống trước đó nếu còn đang chạy
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.stop()
            self.download_thread.wait(1000)
        
        # Reset thanh tiến trình
        self.progress_bar.setValue(0)
        self.speed_label.setText("-- KB/s")
        self.downloaded_label.setText("-- / --")
        self.time_label.setText("--")
        self.progress_group.setVisible(True)
        
        # Tạo nút hủy tải xuống
        self.cancel_download_button = QPushButton("Hủy tải xuống")
        self.cancel_download_button.setObjectName("cancel")
        self.cancel_download_button.clicked.connect(self.cancel_download)
        self.centralWidget().layout().insertWidget(5, self.cancel_download_button)
        
        # Tạo và khởi chạy thread tải xuống
        self.download_thread = FacebookDownloadThread(url, format_id, self.output_path, self.direct_url)
        self.download_thread.progress.connect(self.update_download_progress)
        self.download_thread.finished.connect(self.download_finished)
        self.download_thread.error.connect(self.download_error)
        self.download_thread.start()
        
        # Cập nhật giao diện
        self.download_button.setText("Đang tải...")
        self.download_button.setEnabled(False)
        self.status_bar.showMessage("Đang tải xuống...")

    def cancel_download(self):
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.should_stop = True
            self.download_thread.stop(pause=True)  # Explicitly pause when cancelling
            self.status_bar.showMessage("Đang hủy tải xuống...")
            
            QTimer.singleShot(2000, self.check_download_cancelled)

    def check_download_cancelled(self):
        if not self.download_thread or not self.download_thread.isRunning():
            self.download_button.setEnabled(True)
            self.download_button.setText("Tải xuống")
            self.status_bar.showMessage("Đã hủy tải xuống")
            
            if hasattr(self, 'cancel_download_button') and self.cancel_download_button:
                self.cancel_download_button.setParent(None)
                self.cancel_download_button = None

    def update_download_progress(self, percent, speed, downloaded, remaining_time, total_size):
        self.progress_bar.setValue(percent)
        
        # Hiển thị thông tin theo kiểu mới
        self.speed_label.setText(speed)
        self.downloaded_label.setText(f"{downloaded} / {total_size}")
        self.time_label.setText(remaining_time)
        
        # Cập nhật title window
        self.setWindowTitle(f"Facebook Downloader - {percent}%")
        
        # Đảm bảo progress group hiển thị
        self.progress_group.setVisible(True)

    def download_finished(self, file_path):
        self.download_button.setText("Tải xuống")
        self.download_button.setEnabled(True)
        self.progress_bar.setValue(100)
        self.speed_label.setText("-- KB/s")
        self.downloaded_label.setText("-- / --")
        self.time_label.setText("--")
        self.progress_group.setVisible(False)
        self.status_bar.showMessage(f"Tải xuống hoàn tất: {os.path.basename(file_path)}")
        self.setWindowTitle("Facebook Downloader")
        
        if hasattr(self, 'cancel_download_button') and self.cancel_download_button:
            self.cancel_download_button.setParent(None)
            self.cancel_download_button = None
        
        reply = QMessageBox.question(
            self, 
            "Tải xuống hoàn tất", 
            f"Đã tải xuống xong!\n\nBạn có muốn mở thư mục chứa file không?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.open_file_location(file_path)

    def download_error(self, error):
        self.status_bar.showMessage(f"Lỗi: {error}")
        self.download_button.setText("Tải xuống")
        self.download_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.speed_label.setText("-- KB/s")
        self.downloaded_label.setText("-- / --")
        self.time_label.setText("--")
        self.progress_group.setVisible(False)
        self.setWindowTitle("Facebook Downloader")
        
        if hasattr(self, 'cancel_download_button') and self.cancel_download_button:
            self.cancel_download_button.setParent(None)
            self.cancel_download_button = None
        
        QMessageBox.critical(self, "Lỗi tải xuống", f"Không thể tải xuống: {error}")

    def open_file_location(self, file_path):
        try:
            dir_path = os.path.dirname(file_path)
            if os.name == 'nt':
                os.startfile(dir_path)
            elif os.name == 'posix':
                subprocess.Popen(['xdg-open', dir_path])
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể mở thư mục: {str(e)}")

    def back_to_tool_hub(self):
        # Set flag to indicate we're returning to hub (don't stop downloads)
        self.returning_to_hub = True
        
        # Only stop info thread, let download continue in background
        if self.info_thread and self.info_thread.isRunning():
            self.info_thread.stop()
            self.info_thread.wait()
        
        # Navigate back to main menu
        from ui.main_menu import MainMenu
        self.main_menu = MainMenu()
        self.main_menu.show()
        self.close()
        
    def closeEvent(self, event):
        # Always stop info thread
        if self.info_thread and self.info_thread.isRunning():
            self.info_thread.stop()
            self.info_thread.wait()
        
        # Only stop download thread if not returning to hub
        if not self.returning_to_hub:
            if self.download_thread and self.download_thread.isRunning():
                print("Closing window and stopping Facebook download")
                self.download_thread.stop(pause=True)  # Explicitly pause when closing
                self.download_thread.wait()
        else:
            print("Returning to hub - keeping Facebook download active in background")
        
        event.accept()
