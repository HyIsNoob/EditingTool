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
import random  # Added for device_id generation
import re
import json
from io import BytesIO
from utils.helpers import clean_filename, format_size, format_time
from utils import compat  # Import the compatibility module
import yt_dlp
from utils.download_manager import DownloadManager  # Thêm import DownloadManager

class TikTokInfoThread(QThread):
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
            
            self.progress.emit("Đang tải thông tin video từ TikTok...")
            
            # Check for TikTok URL variations and normalize
            self.progress.emit("Kiểm tra URL TikTok...")
            normalized_url = self.normalize_tiktok_url(self.url)
            if normalized_url != self.url:
                self.url = normalized_url
                self.progress.emit(f"Đã chuẩn hóa URL: {normalized_url}")
            
            # Extract video ID for later use with direct methods
            video_id = self.extract_tiktok_id(self.url)
            self.progress.emit(f"ID video: {video_id}")
            
            # Try multiple extraction methods
            video_info = None
            
            # METHOD 1: Try using yt-dlp with various app emulation settings
            if not video_info:
                video_info = self.extract_with_ytdlp()
            
            # METHOD 2: Try direct web API approach
            if not video_info:
                self.progress.emit("Phương pháp yt-dlp thất bại, thử truy cập trực tiếp web API...")
                video_info = self.extract_from_web_api(video_id)
            
            # METHOD 3: Try using mobile embed page
            if not video_info:
                self.progress.emit("Phương pháp web API thất bại, thử truy cập trang embed...")
                video_info = self.extract_from_embed_page(video_id)
            
            # METHOD 4: Try TikTok mobile page
            if not video_info:
                self.progress.emit("Phương pháp embed thất bại, thử truy cập trang mobile...")
                video_info = self.extract_from_mobile_page(video_id)
                
            # If we have video info, emit it
            if video_info:
                self.info_ready.emit(video_info)
            else:
                # Create a basic fallback response if all methods failed
                self.progress.emit("Tất cả phương pháp thất bại, sử dụng thông tin cơ bản...")
                fallback_info = {
                    'title': f"TikTok Video {video_id}",
                    'uploader': "Unknown",
                    'duration': 0,
                    'thumbnail_url': "",
                    'formats': [
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
                    ],
                    'default_format_index': 0
                }
                self.info_ready.emit(fallback_info)
                
        except Exception as e:
            self.error.emit(f"Lỗi: {str(e)}")

    def extract_with_ytdlp(self):
        """Try extracting video info using yt-dlp with different configurations"""
        extraction_methods = [
            {
                'name': 'Chrome browser emulation',
                'options': {
                    'quiet': True,
                    'no_warnings': True,
                    'socket_timeout': 20,
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                    'referer': 'https://www.tiktok.com/',
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Pragma': 'no-cache',
                        'Cache-Control': 'no-cache'
                    },
                    'extractor_args': {
                        'tiktok': {
                            'app_name': 'trill',
                            'app_version': '30.8.0',
                            'device_id': ''.join(random.choices('0123456789', k=19))
                        }
                    }
                }
            },
            {
                'name': 'Mobile Safari browser emulation',
                'options': {
                    'quiet': True,
                    'no_warnings': True,
                    'socket_timeout': 15,
                    'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
                    'referer': 'https://www.tiktok.com/',
                    'extractor_args': {
                        'tiktok': {
                            'app_name': 'mobile_browser'
                        }
                    }
                }
            },
            {
                'name': 'Latest TikTok app emulation',
                'options': {
                    'quiet': True,
                    'no_warnings': True,
                    'socket_timeout': 15,
                    'extractor_args': {
                        'tiktok': {
                            'app_name': 'tiktok_web',
                            'app_version': '30.8.0',
                            'device_id': ''.join(random.choices('0123456789', k=19)),
                            'use_api': True
                        }
                    }
                }
            },
            {
                'name': 'Basic extraction',
                'options': {
                    'quiet': True,
                    'no_warnings': True,
                    'socket_timeout': 10,
                    'format': 'best'
                }
            }
        ]
        
        for idx, method in enumerate(extraction_methods):
            if self.should_stop:
                return None
                
            try:
                self.progress.emit(f"Thử phương pháp {idx+1}/{len(extraction_methods)}: {method['name']}...")
                
                with yt_dlp.YoutubeDL(method['options']) as ydl:
                    info_dict = ydl.extract_info(self.url, download=False)
                    
                    if info_dict:
                        self.progress.emit(f"Phương pháp {method['name']} thành công!")
                        
                        # Generate format list
                        formats = self.generate_format_list(info_dict)
                        
                        # Create video info structure
                        return {
                            'title': info_dict.get('title', 'TikTok video'),
                            'uploader': info_dict.get('uploader', info_dict.get('creator', 'Unknown user')),
                            'duration': info_dict.get('duration', 0),
                            'thumbnail_url': info_dict.get('thumbnail', ''),
                            'formats': formats,
                            'default_format_index': 0,
                            'webpage_url': info_dict.get('webpage_url', self.url)
                        }
            except Exception as e:
                self.progress.emit(f"Lỗi với phương pháp {method['name']}: {str(e)}")
                continue
        
        self.progress.emit("Tất cả phương pháp yt-dlp thất bại.")
        return None
    
    def extract_from_web_api(self, video_id):
        """Extract video info directly from TikTok web API"""
        try:
            self.progress.emit("Đang truy cập TikTok Web API...")
            
            base_url = "https://www.tiktok.com/api/item/detail/"
            params = {
                'itemId': video_id
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Referer': 'https://www.tiktok.com/',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Origin': 'https://www.tiktok.com'
            }
            
            response = requests.get(base_url, params=params, headers=headers)
            
            if response.status_code != 200:
                self.progress.emit(f"API response code: {response.status_code}")
                return None
            
            data = response.json()
            
            # Check if we have valid data
            if 'itemInfo' not in data or 'itemStruct' not in data['itemInfo']:
                self.progress.emit("API response doesn't contain expected data structure")
                return None
            
            item = data['itemInfo']['itemStruct']
            
            # Get video details
            title = item.get('desc', 'TikTok Video')
            author = item.get('author', {}).get('nickname', 'Unknown')
            duration = item.get('video', {}).get('duration', 0)
            
            # Get thumbnail
            thumbnail_url = ""
            if 'cover' in item.get('video', {}):
                thumbnail_url = item['video']['cover']
            
            # Get video URLs
            video_url = None
            if 'playAddr' in item.get('video', {}):
                video_url = item['video']['playAddr']
            
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
            
            # Return video info
            video_info = {
                'title': title,
                'uploader': author,
                'duration': duration,
                'thumbnail_url': thumbnail_url,
                'formats': formats,
                'default_format_index': 0,
                'direct_url': video_url
            }
            
            return video_info
            
        except Exception as e:
            self.progress.emit(f"Lỗi khi truy cập Web API: {str(e)}")
            return None
    
    def extract_from_embed_page(self, video_id):
        """Extract video info from TikTok embed page"""
        try:
            self.progress.emit("Đang truy cập trang embed...")
            
            embed_url = f"https://www.tiktok.com/embed/v2/{video_id}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.tiktok.com/',
                'Cache-Control': 'no-cache'
            }
            
            response = requests.get(embed_url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                self.progress.emit(f"Embed page response code: {response.status_code}")
                return None
                
            page_content = response.text
            
            # Extract title
            title = "TikTok Video"
            title_match = re.search(r'property="og:title"\s+content="([^"]+)"', page_content)
            if title_match:
                title = title_match.group(1)
            
            # Extract author
            author = "Unknown User"
            author_match = re.search(r'property="og:author"\s+content="([^"]+)"', page_content)
            if author_match:
                author = author_match.group(1)
            
            # Extract thumbnail URL
            thumbnail_url = ""
            thumbnail_match = re.search(r'property="og:image"\s+content="([^"]+)"', page_content)
            if thumbnail_match:
                thumbnail_url = thumbnail_match.group(1)
            
            # Extract video URL - this is the most important part
            video_url = None
            
            # Find all script tags with videoObject
            video_json_match = re.search(r'<script[^>]*type="application/json"[^>]*>([^<]+)</script>', page_content)
            if video_json_match:
                try:
                    json_data = json.loads(video_json_match.group(1))
                    
                    # Search for contentUrl in the JSON data
                    if isinstance(json_data, dict) and 'props' in json_data:
                        props = json_data['props']
                        
                        # Check initialProps.videoData or similar paths
                        if 'initialProps' in props:
                            initial = props['initialProps']
                            if 'videoData' in initial and 'contentUrl' in initial['videoData']:
                                video_url = initial['videoData']['contentUrl']
                            elif 'videoData' in initial and 'playAddr' in initial['videoData']:
                                video_url = initial['videoData']['playAddr']
                except Exception as json_err:
                    self.progress.emit(f"Error parsing embedded JSON: {str(json_err)}")
            
            # If we still don't have a video URL, look for it in the HTML
            if not video_url:
                video_url_match = re.search(r'<video[^>]*src="([^"]+)"', page_content)
                if video_url_match:
                    video_url = video_url_match.group(1)
            
            # If we still don't have a video URL, try another method
            if not video_url:
                video_url_match = re.search(r'\"playAddr\":\"(https:\\\/\\\/[^\"]+)\"', page_content)
                if video_url_match:
                    video_url = video_url_match.group(1).replace('\\/', '/')
            
            # If we STILL don't have a video URL, look for any URL to a video file
            if not video_url:
                video_patterns = [
                    r'(https?://[^"\'>\s]+\.mp4[^"\'>\s]*)',
                    r'(https?://[^"\'>\s]+/play/[^"\'>\s]*)',
                    r'(https?://[^"\'>\s]+\.tiktokcdn\.com[^"\'>\s]*)'
                ]
                
                for pattern in video_patterns:
                    matches = re.findall(pattern, page_content)
                    if matches:
                        video_url = matches[0]
                        break
            
            # If we found a video URL, create video info
            if video_url:
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
                
                return {
                    'title': title,
                    'uploader': author,
                    'duration': 0,  # We don't have duration from embed
                    'thumbnail_url': thumbnail_url,
                    'formats': formats,
                    'default_format_index': 0,
                    'direct_url': video_url
                }
                
            return None
            
        except Exception as e:
            self.progress.emit(f"Lỗi khi truy cập trang embed: {str(e)}")
            return None
    
    def extract_from_mobile_page(self, video_id):
        """Extract video info from TikTok mobile page"""
        try:
            self.progress.emit("Đang truy cập phiên bản mobile...")
            
            mobile_url = f"https://vm.tiktok.com/{video_id}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9'
            }
            
            response = requests.get(mobile_url, headers=headers, timeout=15, allow_redirects=True)
            
            if response.status_code != 200:
                self.progress.emit(f"Mobile page response code: {response.status_code}")
                return None
                
            page_content = response.text
            
            # Try to find video meta info in the page (similar approach to embed page)
            title = "TikTok Video"
            author = "Unknown User"
            thumbnail_url = ""
            video_url = None
            
            # Extract title
            title_match = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', page_content)
            if title_match:
                title = title_match.group(1)
            
            # Extract author
            author_match = re.search(r'<meta\s+name="author"\s+content="([^"]+)"', page_content)
            if author_match:
                author = author_match.group(1)
            
            # Extract thumbnail URL
            thumbnail_match = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', page_content)
            if thumbnail_match:
                thumbnail_url = thumbnail_match.group(1)
            
            # Look for video URL in various formats
            # 1. Look for video tag
            video_url_match = re.search(r'<video[^>]*src="([^"]+)"', page_content)
            if video_url_match:
                video_url = video_url_match.group(1)
            
            # 2. Look for data structures
            if not video_url:
                data_matches = re.findall(r'"playAddr":"([^"]+)"', page_content)
                for match in data_matches:
                    video_url = match.replace('\\u002F', '/').replace('\/', '/')
                    break
            
            # 3. Look for downloadAddr
            if not video_url:
                download_matches = re.findall(r'"downloadAddr":"([^"]+)"', page_content)
                for match in download_matches:
                    video_url = match.replace('\\u002F', '/').replace('\/', '/')
                    break
            
            # 4. Generic MP4 search
            if not video_url:
                mp4_matches = re.findall(r'(https?://[^"\'>\s]+\.mp4[^"\'>\s]*)', page_content)
                if mp4_matches:
                    video_url = mp4_matches[0]
            
            # If we found a video URL, create video info
            if video_url:
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
                
                return {
                    'title': title,
                    'uploader': author,
                    'duration': 0,  # We don't have duration from mobile page
                    'thumbnail_url': thumbnail_url,
                    'formats': formats,
                    'default_format_index': 0,
                    'direct_url': video_url
                }
                
            return None
            
        except Exception as e:
            self.progress.emit(f"Lỗi khi truy cập trang mobile: {str(e)}")
            return None
    
    def generate_format_list(self, info_dict):
        """Generate format list from info_dict"""
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
        if 'formats' in info_dict:
            video_formats = {}
            for f in info_dict.get('formats', []):
                if f.get('vcodec') != 'none' and f.get('height'):
                    height = f.get('height')
                    has_audio = f.get('acodec') != 'none'
                    
                    if height not in video_formats or has_audio:
                        video_formats[height] = f
            
            # Add specific resolution formats
            for height in sorted(video_formats.keys()):
                f = video_formats[height]
                format_id = f['format_id']
                formats.append({
                    'format_id': format_id,
                    'ext': 'mp4',
                    'display_name': f"{height}p",
                    'is_audio': False
                })
        
        return formats
    
    def normalize_tiktok_url(self, url):
        """Normalize various TikTok URL formats to a standard format"""
        # Handle shortened URLs
        if "vm.tiktok.com" in url or "vt.tiktok.com" in url:
            try:
                self.progress.emit("Mở rộng URL rút gọn...")
                response = requests.head(url, allow_redirects=True, timeout=10)
                return response.url
            except Exception as e:
                self.progress.emit(f"Lỗi khi mở rộng URL rút gọn: {str(e)}")
        
        # Handle different URL patterns
        patterns = [
            # Extract username and video ID and reformat
            r'https?://(?:www\.)?tiktok\.com/@([^/]+)/video/(\d+)',
            # Extract just the video ID
            r'https?://(?:www\.)?tiktok\.com/\w+/video/(\d+)',
            # Shared URL format
            r'https?://(?:vt|vm)\.tiktok\.com/(\w+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                if len(match.groups()) == 2:
                    username, video_id = match.groups()
                    return f"https://www.tiktok.com/@{username}/video/{video_id}"
                elif len(match.groups()) == 1:
                    if "tiktok.com/" in pattern:
                        # For normal URLs with just video ID
                        video_id = match.groups()[0]
                        return f"https://www.tiktok.com/video/{video_id}"
        
        return url
    
    def extract_tiktok_id(self, url):
        """Extract TikTok video ID from URL"""
        patterns = [
            r'/@[^/]+/video/(\d+)',
            r'/video/(\d+)',
            r'v/(\d+)',
            r'embed/(\d+)',
            r'embed/v2/(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # For shortened URLs
        if "vm.tiktok.com/" in url or "vt.tiktok.com/" in url:
            parts = url.strip('/').split('/')
            return parts[-1]
        
        # If no pattern matches, extract last numeric segment
        segments = url.split('/')
        for segment in reversed(segments):
            if segment.isdigit():
                return segment
        
        # Default ID
        return "unknown"
    
    def stop(self):
        self.should_stop = True

class TikTokDownloadThread(QThread):
    progress = pyqtSignal(int, str, str, str, str)  # phần trăm, tốc độ, đã tải, thời gian còn lại, tổng kích thước
    finished = pyqtSignal(str)  # file đầu ra
    error = pyqtSignal(str)  # thông báo lỗi
    
    def __init__(self, url, format_id, output_path):
        super().__init__()
        self.url = url
        self.format_id = format_id
        self.output_path = output_path
        self.should_stop = False
        self.download_manager = DownloadManager.get_instance()
        self.download_id = None
        
    def run(self):
        try:
            # Tạo ID tải xuống và thêm vào download manager
            self.download_id = self.download_manager.add_download(
                source='tiktok',
                title=self.url,  # Ban đầu chỉ có URL, cập nhật title sau
                thumbnail_path=None
            )
            
            # Thiết lập các tùy chọn cho yt-dlp
            ydl_opts = {
                'format': self.format_id,
                'outtmpl': os.path.join(self.output_path, '%(title)s.%(ext)s'),
                'noplaylist': True,
                'progress_hooks': [self.progress_hook],
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': False,
                'extractor_args': {
                    'tiktok': {
                        'app_name': 'trill',
                        'app_version': '30.8.0',
                        'device_id': ''.join(random.choices('0123456789', k=19))
                    }
                }
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
                info_dict = ydl.extract_info(self.url, download=True)
                
                # Cập nhật thông tin vào download manager
                if 'title' in info_dict:
                    download_info = self.download_manager.downloads[self.download_id]
                    download_info.title = info_dict['title']
                    
                    # Lưu thumbnail vào thư mục ứng dụng
                    if 'thumbnail' in info_dict:
                        try:
                            thumbnail_url = info_dict['thumbnail']
                            # Lấy thư mục ứng dụng
                            app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
                            # Tạo thư mục thumbnails nếu chưa tồn tại
                            thumbnails_dir = os.path.join(app_dir, "thumbnails")
                            os.makedirs(thumbnails_dir, exist_ok=True)
                            
                            # Tạo tên file thumbnail duy nhất
                            thumbnail_path = os.path.join(thumbnails_dir, f"tiktok_{int(time.time())}_{clean_filename(info_dict['title'])}_thumbnail.jpg")
                            
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
        """Set the file creation and modification time to current time"""
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

class TikTokDownloaderWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KHyTool - TikTok Downloader")
        self.setMinimumSize(900, 650)
        self.showMaximized()
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
                color: #121212;
                font-size: 14px;
            }
            QLabel#header {
                font-size: 32px;
                font-weight: bold;
                color: #FE2C55;
            }
            QLabel#info {
                font-weight: bold;
                color: #121212;
                font-size: 16px;
            }
            QPushButton {
                background-color: #FE2C55;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #FF445F;
            }
            QPushButton:pressed {
                background-color: #E62950;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
            QPushButton#secondary {
                background-color: #25F4EE;
                color: black;
            }
            QPushButton#secondary:hover {
                background-color: #51F6F0;
            }
            QPushButton#secondary:pressed {
                background-color: #20D8D8;
            }
            QPushButton#cancel {
                background-color: #F1F1F2;
                color: #161823;
            }
            QPushButton#cancel:hover {
                background-color: #E3E3E4;
            }
            QPushButton#cancel:pressed {
                background-color: #DADADA;
            }
            QLineEdit {
                border: 1px solid #D3D3D3;
                border-radius: 6px;
                padding: 12px;
                font-size: 16px;
            }
            QLineEdit:focus {
                border: 2px solid #FE2C55;
            }
            QProgressBar {
                border: 1px solid #D3D3D3;
                border-radius: 6px;
                text-align: center;
                height: 24px;
                font-weight: bold;
                font-size: 14px;
            }
            QProgressBar::chunk {
                background-color: #FE2C55;
                border-radius: 5px;
            }
            QComboBox {
                border: 1px solid #D3D3D3;
                border-radius: 6px;
                padding: 10px;
                min-width: 250px;
                font-size: 14px;
            }
            QComboBox:hover {
                border: 1px solid #A0A0A0;
            }
            QComboBox:focus {
                border: 2px solid #FE2C55;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #D3D3D3;
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
                color: #FE2C55;
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
        layout.setContentsMargins(40, 30, 40, 30)  # Tăng padding
        layout.setSpacing(25)  # Tăng spacing

        # Header với thiết kế tối giản, chuyên nghiệp
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(10, 5, 10, 5)
        
        # Header text (loại bỏ emoji logo)
        header_label = QLabel("TikTok Downloader")
        header_label.setObjectName("header")
        header_label.setAlignment(Qt.AlignCenter)
        # Tạo hiệu ứng viền nổi với màu TikTok
        header_label.setStyleSheet("""
            font-size: 36px;
            font-weight: bold;
            color: #FE2C55;
            border-bottom: 3px solid #FE2C55;
            padding-bottom: 5px;
        """)
        header_layout.addWidget(header_label, 1)
        
        layout.addWidget(header_widget)

        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #FE2C55; min-height: 2px;")
        layout.addWidget(separator)

        # URL Input với thiết kế chuyên nghiệp (không dùng emoji)
        input_group = QGroupBox("URL Video")
        input_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #FE2C55;
                border-radius: 12px;
                margin-top: 16px;
                background-color: #ffffff;
                padding: 18px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
                color: #FE2C55;
                background-color: #ffffff;
                font-size: 18px;
            }
        """)
        input_layout = QVBoxLayout(input_group)
        input_layout.setSpacing(15)

        link_layout = QHBoxLayout()
        
        # Loại bỏ icon và tăng kích thước input
        self.link_input = QLineEdit()
        self.link_input.setPlaceholderText("Nhập link TikTok...")
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
        hint_label = QLabel("Ví dụ: https://www.tiktok.com/@username/video/1234567890123456789")
        hint_label.setStyleSheet("font-size: 14px; color: #777777; font-style: italic;")
        input_layout.addWidget(hint_label)
        
        layout.addWidget(input_group)

        # Video Info Panel
        info_group = QGroupBox("Thông tin Video")
        info_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #25F4EE;
                border-radius: 12px;
                margin-top: 16px;
                background-color: #ffffff;
                padding: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
                color: #25F4EE;
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
                border: 2px solid #25F4EE;
                border-radius: 10px;
                padding: 2px;
            }
        """)
        thumbnail_layout = QVBoxLayout(thumbnail_frame)
        thumbnail_layout.setContentsMargins(0, 0, 0, 0)
        
        # Chuẩn hóa kích thước thumbnail theo tỷ lệ TikTok (thường là 9:16 nhưng dùng 16:9 cho giao diện nhất quán)
        self.thumbnail_label = QLabel("Thumbnail sẽ hiển thị ở đây")
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setFixedSize(320, 180)  # Kích thước chuẩn giống YouTube
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
            color: #121212;
            padding: 8px;
            background-color: #f0f0f0;
            border-left: 4px solid #FE2C55;
            min-height: 20px;
        """)
        self.title_label.setMinimumHeight(50)
        details_layout.addWidget(self.title_label)
        
        # Uploader/Author
        self.uploader_label = QLabel("Tác giả: ")
        self.uploader_label.setObjectName("info")
        self.uploader_label.setWordWrap(True)
        self.uploader_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #121212;
            padding: 8px;
            background-color: #f0f0f0;
            border-left: 4px solid #25F4EE;
            min-height: 20px;
        """)
        self.uploader_label.setMinimumHeight(40)
        details_layout.addWidget(self.uploader_label)
        
        # Duration
        self.duration_label = QLabel("Thời lượng: ")
        self.duration_label.setObjectName("info")
        self.duration_label.setWordWrap(True)
        self.duration_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #121212;
            padding: 8px;
            background-color: #f0f0f0;
            border-left: 4px solid #161823;
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
                border: 2px solid #FE2C55;
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
        path_group = QGroupBox("Đường dẫn lưu file")
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
        path_button.setMinimumWidth(150)
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
                background-color: #FE2C55;
                color: white;
                border-radius: 8px;
                padding: 15px 30px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FF445F;
            }
            QPushButton:pressed {
                background-color: #E62950;
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
        self.speed_label.setFont(QFont("Arial", 16, QFont.Bold))
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
        self.downloaded_label.setFont(QFont("Arial", 16, QFont.Bold))
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

        # Status Bar với style mới
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("QStatusBar { color: #121212; font-size: 14px; padding: 5px; }")
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Sẵn sàng tải video từ TikTok")

    def fetch_video_info(self):
        url = self.link_input.text().strip()
        if not url:
            self.status_bar.showMessage("Vui lòng nhập link TikTok")
            return
        
        # Kiểm tra xem URL có phải là TikTok không
        if "tiktok.com" not in url and "douyin.com" not in url:
            QMessageBox.warning(self, "URL không hợp lệ", "Link không phải là TikTok. Vui lòng kiểm tra lại.")
            return
        
        # Hủy thread trước đó nếu đang chạy
        if self.info_thread and self.info_thread.isRunning():
            self.info_thread.stop()
            self.info_thread.wait(1000)
        
        # Cập nhật UI để hiển thị đang tải
        self.thumbnail_label.setText("Đang tải thông tin...")
        self.title_label.setText("Tiêu đề: Đang tải...")
        self.uploader_label.setText("Tác giả: Đang tải...")
        self.duration_label.setText("Thời lượng: Đang tải...")
        self.format_combo.clear()
        self.format_combo.setEnabled(False)  # Vô hiệu hóa combo box khi đang tải
        self.format_combo.setPlaceholderText("Đang tải danh sách chất lượng...")
        self.download_button.setEnabled(False)
        
        # Tạo và khởi chạy thread lấy thông tin
        self.info_thread = TikTokInfoThread(url)
        self.info_thread.info_ready.connect(self.update_video_info)
        self.info_thread.error.connect(self.handle_info_error)
        self.info_thread.progress.connect(self.update_fetch_progress)
        self.info_thread.finished.connect(self.info_thread_finished)
        self.info_thread.start()
        
        self.status_bar.showMessage("Đang tải thông tin video...")

    def update_fetch_progress(self, message):
        self.status_bar.showMessage(message)
    
    def cancel_fetch(self):
        if self.info_thread and self.info_thread.isRunning():
            self.info_thread.stop()
        
        if hasattr(self, 'cancel_button') and self.cancel_button:
            self.cancel_button.setParent(None)
            self.cancel_button = None
        
        self.title_label.setText("Tiêu đề: Đã hủy")
        self.status_bar.showMessage("Đã hủy lấy thông tin video")

    def update_video_info(self, info):
        # Cập nhật thông tin video lên UI
        
        # Kiểm tra và giới hạn độ dài tiêu đề
        title = info['title']
        if len(title) > 80:  # Giới hạn độ dài hiển thị
            title = title[:77] + "..."
        self.title_label.setText(f"Tiêu đề: {title}")
        
        # Kiểm tra và giới hạn độ dài tên tác giả
        uploader = info['uploader']
        if len(uploader) > 50:  # Giới hạn độ dài hiển thị
            uploader = uploader[:47] + "..."
        self.uploader_label.setText(f"Tác giả: {uploader}")
        
        # Định dạng thời lượng
        duration_text = format_time(info['duration']) if info['duration'] > 0 else "Không rõ"
        self.duration_label.setText(f"Thời lượng: {duration_text}")
        
        # Tải và hiển thị thumbnail
        try:
            if info['thumbnail_url']:
                response = requests.get(info['thumbnail_url'])
                if response.status_code == 200:
                    pixmap = QPixmap()
                    pixmap.loadFromData(BytesIO(response.content).read())
                    # Thay đổi tỷ lệ khung hình, giữ AspectRatioMode là KeepAspectRatio để không bị méo
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
        
        # Đặt format mặc định (thường là chất lượng cao nhất)
        if len(info['formats']) > 0:
            self.format_combo.setCurrentIndex(0)
        
        # Bật nút tải xuống
        self.download_button.setEnabled(True)
        self.status_bar.showMessage(f"Đã tải thông tin video: {info['title']}")

    def handle_info_error(self, error):
        self.status_bar.showMessage(f"Lỗi: {error}")
        self.thumbnail_label.setText(f"Lỗi: {error}")
        self.title_label.setText("Tiêu đề: --")
        self.uploader_label.setText("Tác giả: --")
        self.duration_label.setText("Thời lượng: --")
        
        # Xử lý combo box
        self.format_combo.clear()
        self.format_combo.setEnabled(False)  # Vô hiệu hóa combo box khi có lỗi
        self.format_combo.setPlaceholderText("Chọn chất lượng")
        
        # Vô hiệu hóa nút tải xuống
        self.download_button.setEnabled(False)
        
        # Thông báo lỗi cho người dùng
        QMessageBox.critical(self, "Lỗi", f"Không thể tải thông tin video: {error}")

    def info_thread_finished(self):
        if hasattr(self, 'cancel_button') and self.cancel_button:
            self.cancel_button.setParent(None)
            self.cancel_button = None

    def select_output_path(self):
        path = QFileDialog.getExistingDirectory(self, "Chọn đường dẫn tải về", self.output_path)
        if path:
            self.output_path = path
            self.path_label.setText(f"Đường dẫn tải về: {self.output_path}")

    def download_video(self):
        url = self.link_input.text().strip()
        format_id = self.format_combo.currentData()
        
        if not url:
            self.status_bar.showMessage("Vui lòng nhập link TikTok")
            return
        
        if not format_id:
            self.status_bar.showMessage("Vui lòng chọn định dạng tải xuống")
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
        self.download_thread = TikTokDownloadThread(url, format_id, self.output_path)
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
        
        # Hiển thị thông tin theo kiểu mới, riêng biệt
        self.speed_label.setText(speed)
        self.downloaded_label.setText(f"{downloaded} / {total_size}")
        self.time_label.setText(remaining_time)
        
        # Cập nhật title window
        self.setWindowTitle(f"TikTok Downloader - {percent}%")
        
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
        self.setWindowTitle("TikTok Downloader")
        
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
        self.setWindowTitle("TikTok Downloader")
        
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
                print("Closing window and stopping TikTok download")
                self.download_thread.stop(pause=True)  # Explicitly pause when closing
                self.download_thread.wait()
        else:
            print("Returning to hub - keeping TikTok download active in background")
        
        event.accept()
