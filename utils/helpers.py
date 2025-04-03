import os
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt

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

def clean_filename(filename):
    """Xóa các ký tự không hợp lệ trong tên file"""
    import re
    invalid_chars = r'[\\/*?:"<>|]'
    return re.sub(invalid_chars, '', filename)

def format_size(size_bytes):
    """Format kích thước file thành dạng dễ đọc"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.1f} MB"
    else:
        return f"{size_bytes / 1024 / 1024 / 1024:.1f} GB"

def format_time(seconds):
    """Format thời gian theo giây thành dạng dễ đọc"""
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds} giây"
    elif seconds < 3600:
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes} phút {seconds} giây"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours} giờ {minutes} phút"

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
