import os
import json
import sys
import platform
from typing import Dict, Any, Optional

class ConfigManager:
    """
    Lớp quản lý cấu hình ứng dụng.
    Sử dụng singleton pattern để đảm bảo chỉ có một instance duy nhất.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # Xác định đường dẫn cấu hình
        self._app_name = "KHyTool"
        self._config_file = os.path.join(self._get_config_dir(), "config.json")
        
        # Giá trị mặc định
        self._defaults = {
            "general": {
                "language": "vi",
                "theme": "light",
                "check_updates": True,
                "first_run": True
            },
            "directories": {
                "projects_dir": os.path.join(os.path.expanduser("~"), "KHyTool Projects"),
                "downloads_dir": os.path.join(os.path.expanduser("~"), "Downloads"),
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
                "download_dir": os.path.expanduser("~/Downloads")
            },
            "audio_separator": {
                "output_dir": os.path.expanduser("~/SeparatedAudio"),
                "model": "demucs"
            },
            "window_state": {
                "main_geometry": None,
                "main_state": None
            }
        }
        
        # Tạo thư mục chứa file cấu hình nếu chưa tồn tại
        os.makedirs(os.path.dirname(self._config_file), exist_ok=True)
        
        # Tải cấu hình từ file hoặc sử dụng mặc định
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
            return config
        except Exception as e:
            print(f"Lỗi khi đọc file cấu hình: {e}")
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
            return True
        except Exception as e:
            print(f"Lỗi khi lưu file cấu hình: {e}")
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
        return self.get("directories", "downloads_dir", os.path.expanduser("~/Downloads"))
    
    @downloads_dir.setter
    def downloads_dir(self, value: str) -> None:
        self.set("directories", "downloads_dir", value)
    
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
        return self.get("downloader", "download_dir", os.path.expanduser("~/Downloads"))
    
    @download_dir.setter
    def download_dir(self, value: str) -> None:
        self.set("downloader", "download_dir", value)
    
    # Audio separator settings
    @property
    def audio_output_dir(self) -> str:
        return self.get("audio_separator", "output_dir", 
                       os.path.expanduser("~/SeparatedAudio"))
    
    @audio_output_dir.setter
    def audio_output_dir(self, value: str) -> None:
        self.set("audio_separator", "output_dir", value)

# Ví dụ sử dụng:
# config = ConfigManager()
# print(config.language)
# config.language = "en"
# config.save()