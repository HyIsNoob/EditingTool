import os
import json
import sys
import platform
import logging
from typing import Dict, Any, Optional

class ConfigManager:
    """
    Lớp quản lý cấu hình ứng dụng.
    Sử dụng singleton pattern để đảm bảo chỉ có một instance duy nhất.
    """
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ConfigManager()
        return cls._instance
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Define application name and paths
        self._app_name = "KHyTool"
        
        # Get the application's base directory
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        except Exception:
            # Fallback if running from a packaged app
            base_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
        
        # Config directory - create in the app's directory
        self._config_dir = os.path.join(base_dir, "config")
        os.makedirs(self._config_dir, exist_ok=True)
        
        # Path to the config file
        self._config_file = os.path.join(self._config_dir, "settings.json")
        
        # Default configuration values
        self._defaults = {
            "general": {
                "language": "vi",
                "theme": "light",
                "check_updates": True,
                "first_run": True,
                "auto_reload_projects": True  # Add auto-reload setting
            },
            "directories": {
                "projects_dir": os.path.join(os.path.expanduser("~"), "KHyTool Projects"),
                "downloads_dir": os.path.expanduser("~/Downloads"),
                "last_opened_project": None,
                "last_opened_file": None
            },
            "ocr": {
                "tesseract_path": self._get_default_tesseract_path(),
                "default_language": "vie",
                "auto_rotate": True,
                "auto_enhance": True
            },
            "subtitle": {
                "whisper_model": "base",
                "default_language": "vi",
                "segment_length": 10,
                "models_dir": os.path.join(self._get_app_dir(), "models", "whisper")
            },
            "downloader": {
                "youtube_quality": "best",
                "tiktok_quality": "best",
                "facebook_quality": "best",
                "download_dir": os.path.expanduser("~/Downloads"),
                "thumbnail_cleanup": {
                    "enabled": True,
                    "max_age_days": 7,
                    "max_count": 500,
                    "last_cleanup": None
                }
            },
            "audio_separator": {
                "output_dir": os.path.expanduser("~/SeparatedAudio"),
                "model": "demucs"
            },
            "window_state": {
                "main_geometry": None,
                "main_state": None
            },
            "recent_projects": []
        }
        
        # Load the configuration
        self._config = self._load_config()
        
        self._initialized = True
    
    def _get_config_dir(self) -> str:
        """Xác định thư mục chứa file cấu hình dựa trên hệ điều hành"""
        system = platform.system()
        if system == "Windows":
            # Trên Windows: %APPDATA%\KHyTool
            return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), self._app_name)
        elif system == "Darwin":  # macOS
            # Trên macOS: ~/Library/Application Support/KHyTool
            return os.path.join(os.path.expanduser("~"), "Library", "Application Support", self._app_name)
        else:  # Linux và các hệ điều hành khác
            # Trên Linux: ~/.config/KHyTool
            return os.path.join(os.path.expanduser("~"), ".config", self._app_name)
    
    def _get_app_dir(self) -> str:
        """Xác định thư mục gốc của ứng dụng"""
        if getattr(sys, 'frozen', False):
            # Nếu ứng dụng được đóng gói (PyInstaller)
            return os.path.dirname(sys.executable)
        else:
            # Nếu đang chạy từ mã nguồn
            return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def _get_default_tesseract_path(self) -> str:
        """Xác định đường dẫn mặc định của Tesseract OCR"""
        system = platform.system()
        if system == "Windows":
            return r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        elif system == "Darwin":  # macOS
            return "/usr/local/bin/tesseract"
        else:  # Linux và các hệ điều hành khác
            return "/usr/bin/tesseract"
    
    def _load_config(self) -> Dict[str, Any]:
        """Đọc cấu hình từ file, nếu không có thì sử dụng mặc định"""
        if not os.path.exists(self._config_file):
            return self._defaults.copy()
        
        try:
            with open(self._config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # Cập nhật cấu hình với các giá trị mặc định nếu thiếu
            self._update_missing_keys(config, self._defaults)
            self.logger.info(f"Configuration loaded from {self._config_file}")
            return config
        except Exception as e:
            self.logger.error(f"Lỗi khi đọc file cấu hình: {e}")
            return self._defaults.copy()
    
    def _update_missing_keys(self, config: Dict[str, Any], defaults: Dict[str, Any]) -> None:
        """Cập nhật các key thiếu trong config từ defaults"""
        for key, value in defaults.items():
            if key not in config:
                config[key] = value
            elif isinstance(value, dict) and isinstance(config[key], dict):
                # Đệ quy cho các dict lồng nhau
                self._update_missing_keys(config[key], value)
    
    def save(self) -> bool:
        """Lưu cấu hình hiện tại xuống file"""
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
            self.logger.info(f"Configuration saved to {self._config_file}")
            return True
        except Exception as e:
            self.logger.error(f"Lỗi khi lưu file cấu hình: {e}")
            return False
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Lấy giá trị cấu hình từ section và key"""
        try:
            return self._config.get(section, {}).get(key, default)
        except Exception:
            return default
    
    def set(self, section: str, key: str, value: Any) -> None:
        """Thiết lập giá trị cấu hình cho section và key"""
        if section not in self._config:
            self._config[section] = {}
        self._config[section][key] = value
    
    def get_all(self) -> Dict[str, Any]:
        """Lấy toàn bộ cấu hình"""
        return self._config.copy()
    
    def reset_to_defaults(self) -> None:
        """Đặt lại cấu hình về mặc định"""
        self._config = self._defaults.copy()
        self.save()
    
    def get_download_dir(self) -> str:
        """Get the shared download directory path"""
        return self._config.get("downloader", {}).get("download_dir", self._defaults["downloader"]["download_dir"])
    
    def set_download_dir(self, path: str) -> None:
        """Set the shared download directory path"""
        self.set("downloader", "download_dir", path)
        self.save()
        self.logger.info(f"Download directory changed to {path}")
    
    def add_recent_project(self, project_path: str) -> None:
        """Add a project to the recent projects list"""
        recent_projects = self._config.get("recent_projects", [])
        
        # Remove if already exists
        if project_path in recent_projects:
            recent_projects.remove(project_path)
        
        # Add to beginning
        recent_projects.insert(0, project_path)
        
        # Keep only 10 most recent
        self._config["recent_projects"] = recent_projects[:10]
        self.save()
    
    def get_recent_projects(self) -> list:
        """Get list of recent projects"""
        return self._config.get("recent_projects", [])
    
    # === Các getter/setter tiện ích cho các thiết lập phổ biến ===
    
    # General settings
    @property
    def language(self) -> str:
        return self.get("general", "language", "vi")
    
    @language.setter
    def language(self, value: str) -> None:
        self.set("general", "language", value)
    
    @property
    def theme(self) -> str:
        return self.get("general", "theme", "light")
    
    @theme.setter
    def theme(self, value: str) -> None:
        self.set("general", "theme", value)
    
    # Directory settings
    @property
    def projects_dir(self) -> str:
        return self.get("directories", "projects_dir", 
                        os.path.join(os.path.expanduser("~"), "KHyTool Projects"))
    
    @projects_dir.setter
    def projects_dir(self, value: str) -> None:
        self.set("directories", "projects_dir", value)
    
    @property
    def downloads_dir(self) -> str:
        return self.get_download_dir()
    
    @downloads_dir.setter
    def downloads_dir(self, value: str) -> None:
        self.set_download_dir(value)
    
    @property
    def last_opened_project(self) -> Optional[str]:
        return self.get("directories", "last_opened_project")
    
    @last_opened_project.setter
    def last_opened_project(self, value: str) -> None:
        self.set("directories", "last_opened_project", value)
    
    # OCR settings
    @property
    def tesseract_path(self) -> str:
        return self.get("ocr", "tesseract_path", self._get_default_tesseract_path())
    
    @tesseract_path.setter
    def tesseract_path(self, value: str) -> None:
        self.set("ocr", "tesseract_path", value)
    
    @property
    def ocr_language(self) -> str:
        return self.get("ocr", "default_language", "vie")
    
    @ocr_language.setter
    def ocr_language(self, value: str) -> None:
        self.set("ocr", "default_language", value)
    
    # Subtitle settings
    @property
    def whisper_model(self) -> str:
        return self.get("subtitle", "whisper_model", "base")
    
    @whisper_model.setter
    def whisper_model(self, value: str) -> None:
        self.set("subtitle", "whisper_model", value)
    
    @property
    def whisper_models_dir(self) -> str:
        return self.get("subtitle", "models_dir", 
                       os.path.join(self._get_app_dir(), "models", "whisper"))
    
    @property
    def subtitle_language(self) -> str:
        return self.get("subtitle", "default_language", "vi")
    
    @subtitle_language.setter
    def subtitle_language(self, value: str) -> None:
        self.set("subtitle", "default_language", value)
    
    # Downloader settings
    @property
    def youtube_quality(self) -> str:
        return self.get("downloader", "youtube_quality", "best")
    
    @youtube_quality.setter
    def youtube_quality(self, value: str) -> None:
        self.set("downloader", "youtube_quality", value)
    
    @property
    def download_dir(self) -> str:
        return self.get_download_dir()
    
    @download_dir.setter
    def download_dir(self, value: str) -> None:
        self.set_download_dir(value)
    
    # Audio separator settings
    @property
    def audio_output_dir(self) -> str:
        return self.get("audio_separator", "output_dir", 
                       os.path.expanduser("~/SeparatedAudio"))
    
    @audio_output_dir.setter
    def audio_output_dir(self, value: str) -> None:
        self.set("audio_separator", "output_dir", value)
    
    # Thumbnail cleaning settings
    @property
    def thumbnail_cleanup_enabled(self) -> bool:
        """Get if thumbnail cleanup is enabled"""
        return self.get("downloader", "thumbnail_cleanup", {}).get("enabled", True)
    
    @thumbnail_cleanup_enabled.setter
    def thumbnail_cleanup_enabled(self, value: bool) -> None:
        """Set if thumbnail cleanup is enabled"""
        if "thumbnail_cleanup" not in self._config.get("downloader", {}):
            self._config["downloader"]["thumbnail_cleanup"] = {}
        self._config["downloader"]["thumbnail_cleanup"]["enabled"] = value
        self.save()
    
    @property
    def thumbnail_max_age_days(self) -> int:
        """Get maximum age in days for thumbnails before cleanup"""
        return self.get("downloader", "thumbnail_cleanup", {}).get("max_age_days", 7)
    
    @thumbnail_max_age_days.setter
    def thumbnail_max_age_days(self, value: int) -> None:
        """Set maximum age in days for thumbnails before cleanup"""
        if "thumbnail_cleanup" not in self._config.get("downloader", {}):
            self._config["downloader"]["thumbnail_cleanup"] = {}
        self._config["downloader"]["thumbnail_cleanup"]["max_age_days"] = value
        self.save()
    
    @property
    def thumbnail_max_count(self) -> int:
        """Get maximum number of thumbnails to keep"""
        return self.get("downloader", "thumbnail_cleanup", {}).get("max_count", 500)
    
    @thumbnail_max_count.setter
    def thumbnail_max_count(self, value: int) -> None:
        """Set maximum number of thumbnails to keep"""
        if "thumbnail_cleanup" not in self._config.get("downloader", {}):
            self._config["downloader"]["thumbnail_cleanup"] = {}
        self._config["downloader"]["thumbnail_cleanup"]["max_count"] = value
        self.save()
    
    @property
    def thumbnail_last_cleanup(self) -> float:
        """Get timestamp of last thumbnail cleanup"""
        return self.get("downloader", "thumbnail_cleanup", {}).get("last_cleanup")
    
    @thumbnail_last_cleanup.setter
    def thumbnail_last_cleanup(self, value: float) -> None:
        """Set timestamp of last thumbnail cleanup"""
        if "thumbnail_cleanup" not in self._config.get("downloader", {}):
            self._config["downloader"]["thumbnail_cleanup"] = {}
        self._config["downloader"]["thumbnail_cleanup"]["last_cleanup"] = value
        self.save()
    
    # Auto-reload setting
    @property
    def auto_reload_projects(self) -> bool:
        """Get if projects should auto-reload when files change"""
        return self.get("general", "auto_reload_projects", True)
    
    @auto_reload_projects.setter
    def auto_reload_projects(self, value: bool) -> None:
        """Set if projects should auto-reload when files change"""
        self.set("general", "auto_reload_projects", value)
        self.save()

# Ví dụ sử dụng:
# config = ConfigManager.get_instance()
# print(config.language)
# config.language = "en"
# config.save()