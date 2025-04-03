import os
import re
import time
from datetime import datetime
import logging
from typing import List, Tuple
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt

# Initialize logger
logger = logging.getLogger(__name__)

def show_error_message(parent, title, message):
    """Hiển thị thông báo lỗi"""
    QMessageBox.critical(parent, title, message)

def show_info_message(parent, title, message):
    """Hiển thị thông báo thông tin"""
    QMessageBox.information(parent, title, message)

def convert_qimage_to_pixmap(qimage):
    """Chuyển đổi QImage thành QPixmap"""
    return QPixmap.fromImage(qimage)

def load_image_from_path(image_path):
    """Tải ảnh từ đường dẫn"""
    if not os.path.exists(image_path):
        return None
    
    pixmap = QPixmap(image_path)
    if pixmap.isNull():
        return None
    
    return pixmap

def clean_filename(filename: str) -> str:
    """Cleans a filename by removing invalid characters and replacing spaces."""
    # Replace any non-alphanumeric/non-space characters with underscores
    clean = re.sub(r'[^\w\s\.-]', '_', filename)
    # Replace multiple spaces with a single underscore
    clean = re.sub(r'\s+', '_', clean)
    return clean

def format_size(size_bytes: int) -> str:
    """Format file size from bytes to human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024):.1f} MB"
    else:
        return f"{size_bytes/(1024*1024*1024):.1f} GB"

def format_time(seconds: int) -> str:
    """Format time in seconds to human-readable format."""
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes} minutes {secs} seconds"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours} hours {minutes} minutes {secs} seconds"

def clean_thumbnails(thumbnails_dir: str, max_age_days: int = 7, max_count: int = 500) -> Tuple[int, int]:
    """
    Clean thumbnail files to prevent storage bloat.
    
    Args:
        thumbnails_dir: Directory where thumbnails are stored
        max_age_days: Maximum age in days for thumbnails before deletion
        max_count: Maximum number of thumbnails to keep
        
    Returns:
        Tuple of (number of files deleted by age, number of files deleted by count)
    """
    if not os.path.exists(thumbnails_dir):
        logger.warning(f"Thumbnail directory not found: {thumbnails_dir}")
        return (0, 0)
    
    # Get all thumbnail files
    thumbnail_files = []
    for filename in os.listdir(thumbnails_dir):
        file_path = os.path.join(thumbnails_dir, filename)
        # Skip directories and non-image files
        if os.path.isdir(file_path):
            continue
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp')):
            continue
            
        # Get file info
        try:
            mtime = os.path.getmtime(file_path)
            size = os.path.getsize(file_path)
            thumbnail_files.append((file_path, mtime, size))
        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {str(e)}")
    
    # No thumbnails to clean
    if not thumbnail_files:
        return (0, 0)
    
    # Step 1: Delete old thumbnails
    now = time.time()
    max_age_seconds = max_age_days * 24 * 60 * 60
    age_deleted = 0
    
    for file_path, mtime, _ in thumbnail_files[:]:
        if now - mtime > max_age_seconds:
            try:
                os.remove(file_path)
                thumbnail_files.remove((file_path, mtime, _))
                age_deleted += 1
                logger.debug(f"Deleted old thumbnail: {file_path}")
            except Exception as e:
                logger.error(f"Error deleting thumbnail {file_path}: {str(e)}")
    
    # Step 2: If we still have too many thumbnails, delete the oldest ones
    count_deleted = 0
    if len(thumbnail_files) > max_count:
        # Sort by modification time (oldest first)
        thumbnail_files.sort(key=lambda x: x[1])
        
        # Delete excess thumbnails
        excess_count = len(thumbnail_files) - max_count
        for file_path, _, _ in thumbnail_files[:excess_count]:
            try:
                os.remove(file_path)
                count_deleted += 1
                logger.debug(f"Deleted excess thumbnail: {file_path}")
            except Exception as e:
                logger.error(f"Error deleting thumbnail {file_path}: {str(e)}")
    
    logger.info(f"Thumbnail cleanup: {age_deleted} files deleted by age, {count_deleted} files deleted by count")
    return (age_deleted, count_deleted)

def check_and_clean_thumbnails():
    """
    Check if thumbnail cleanup is needed and perform cleanup if necessary.
    This is meant to be called at application startup.
    """
    try:
        # Import here to avoid circular import
        from utils.config_manager import ConfigManager
        
        config = ConfigManager.get_instance()
        
        # Skip if thumbnail cleanup is disabled
        if not config.thumbnail_cleanup_enabled:
            return
        
        # Get the last cleanup time
        last_cleanup = config.thumbnail_last_cleanup
        now = time.time()
        
        # If never cleaned or more than 3 days since last cleanup
        if last_cleanup is None or (now - last_cleanup > 3 * 24 * 60 * 60):
            # Get the app's directory
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            thumbnails_dir = os.path.join(app_dir, "thumbnails")
            
            # Perform cleanup
            age_deleted, count_deleted = clean_thumbnails(
                thumbnails_dir,
                config.thumbnail_max_age_days,
                config.thumbnail_max_count
            )
            
            # Update last cleanup time
            config.thumbnail_last_cleanup = now
            
            logger.info(f"Automated thumbnail cleanup completed. Deleted {age_deleted + count_deleted} files.")
    except Exception as e:
        logger.error(f"Error during thumbnail cleanup check: {str(e)}")

def get_stylesheet():
    """Stylesheet chung cho ứng dụng"""
    return """
        QMainWindow {
            background-color: #f5f5f5;
        }
        QLabel {
            font-size: 12px;
            color: #333;
        }
        QPushButton {
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:pressed {
            background-color: #3d8b40;
        }
        QPushButton:disabled {
            background-color: #cccccc;
            color: #666666;
        }
        QTextEdit {
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 8px;
            background-color: white;
        }
        QComboBox {
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 4px 8px;
            background-color: white;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox QAbstractItemView {
            border: 1px solid #ddd;
            selection-background-color: #4CAF50;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin-top: 12px;
            padding-top: 8px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px;
        }
        QScrollBar:vertical {
            border: none;
            background: #f5f5f5;
            width: 10px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: #ccc;
            min-height: 30px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover {
            background: #999;
        }
    """
