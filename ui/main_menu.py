import os  # Ensure this is at the top of the file
import sys
import subprocess
import time
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QWidget, QLabel, QGroupBox, QGridLayout, QSpacerItem,
                            QSizePolicy, QFrame, QGraphicsDropShadowEffect, QListWidget, QListWidgetItem, QSplitter, QProgressBar, QMessageBox, QTabWidget)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QIcon, QFont, QPixmap, QColor, QPalette
from ui.project_manager_window import ProjectManagerWindow
from ui.youtube_downloader_window import YouTubeDownloaderWindow
from ui.tiktok_downloader_window import TikTokDownloaderWindow
from ui.facebook_downloader_window import FacebookDownloaderWindow
from utils.download_manager import DownloadManager

class RoundedFeatureCard(QFrame):
    """Enhanced feature card with rounded corners, shadow, and decorative elements"""
    def __init__(self, title, description, emoji, primary=False, parent=None):
        super().__init__(parent)
        
        self.title = title
        self.description = description
        self.emoji = emoji
        self.primary = primary
        
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title with emoji
        title_layout = QHBoxLayout()
        
        # Add emoji
        emoji_label = QLabel(self.emoji)
        emoji_label.setFont(QFont("Segoe UI Emoji", 22))
        emoji_label.setStyleSheet("background-color: transparent;")
        title_layout.addWidget(emoji_label)
        
        # Add title
        title_label = QLabel(self.title)
        font_size = 18 if self.primary else 16
        title_font = QFont("Arial", font_size, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {'#2E7D32' if self.primary else '#333'}; background-color: transparent;")
        title_layout.addWidget(title_label, 1)
        
        layout.addLayout(title_layout)
        
        # Description
        desc_label = QLabel(self.description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #555; font-size: 20px; background-color: transparent;")
        desc_label.setMinimumHeight(50)
        layout.addWidget(desc_label)
        
        # Action button
        self.action_button = QPushButton()
        self.action_button.setFont(QFont("Arial", 14, QFont.Bold))
        self.action_button.setStyleSheet("""
            QPushButton {
                background-color: #2E7D32;
                color: white;
                border-radius: 8px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
            QPushButton:pressed {
                background-color: #1B5E20;
            }
        """)
        layout.addWidget(self.action_button)


class DownloadItemWidget(QWidget):
    """Custom widget for download list items with buttons"""
    
    def __init__(self, download_id, title, status, thumbnail_path, progress, output_file, parent=None):
        super().__init__(parent)
        self.download_id = download_id
        self.output_file = output_file
        self.parent_menu = parent
        # Add these new lines for list tracking
        self.list_widget = None  # Will be set after widget is added to list
        
        # Setup layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Thumbnail (left side)
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(120, 68)
        self.thumbnail_label.setStyleSheet("border: 1px solid #ddd; background-color: #f0f0f0;")
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        
        if thumbnail_path and os.path.exists(thumbnail_path):
            pixmap = QPixmap(thumbnail_path)
            self.thumbnail_label.setPixmap(pixmap.scaled(120, 68, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            # Default icons based on source
            if title.startswith("YouTube") or "youtube.com" in title.lower():
                self.thumbnail_label.setText("YouTube")
                self.thumbnail_label.setStyleSheet("background-color: #FF0000; color: white; font-weight: bold;")
            elif title.startswith("TikTok") or "tiktok.com" in title.lower():
                self.thumbnail_label.setText("TikTok")
                self.thumbnail_label.setStyleSheet("background-color: #000000; color: white; font-weight: bold;")
            elif title.startswith("Facebook") or "facebook.com" in title.lower():
                self.thumbnail_label.setText("Facebook")
                self.thumbnail_label.setStyleSheet("background-color: #1877F2; color: white; font-weight: bold;")
            else:
                self.thumbnail_label.setText("Video")
                
        layout.addWidget(self.thumbnail_label)
        
        # Info (middle)
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(5, 0, 5, 0)
        info_layout.setSpacing(5)
        
        # Title with ellipsis for long names
        title_text = title if len(title) <= 40 else title[:37] + "..."
        title_label = QLabel(title_text)
        title_label.setStyleSheet("font-weight: bold; color: #333;")
        info_layout.addWidget(title_label)
        
        # Progress bar
        if status == 'downloading' or status == 'processing':
            progress_bar = QProgressBar()
            progress_bar.setValue(progress if progress else 0)
            progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #ddd;
                    border-radius: 3px;
                    text-align: center;
                    height: 16px;
                }
                QProgressBar::chunk {
                    background-color: #2196F3;
                    border-radius: 2px;
                }
            """)
            info_layout.addWidget(progress_bar)
        else:
            status_text = "✅ Hoàn tất" if status == 'completed' else "❌ Lỗi" if status == 'error' else "⬇️ Đang tải"
            status_label = QLabel(status_text)
            status_label.setStyleSheet("color: #666;")
            info_layout.addWidget(status_label)
        
        layout.addWidget(info_widget, 1)
        
        # Action buttons (right side)
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(5)
        
        # Only enable buttons if download completed and file exists
        can_open = status == 'completed' and output_file and os.path.exists(output_file)
        
        # Play button
        play_button = QPushButton("▶️ Phát")
        play_button.setToolTip("Mở file đã tải")
        play_button.setFixedHeight(30)
        play_button.setCursor(Qt.PointingHandCursor)
        play_button.setEnabled(can_open)
        play_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 4px;
                padding: 3px 8px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #cccccc; color: #666666; }
        """)
        play_button.clicked.connect(self.open_file)
        buttons_layout.addWidget(play_button)
        
        # Folder button
        folder_button = QPushButton("📂 Thư mục")
        folder_button.setToolTip("Mở thư mục chứa file")
        folder_button.setFixedHeight(30)
        folder_button.setCursor(Qt.PointingHandCursor)
        folder_button.setEnabled(can_open)
        folder_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 4px;
                padding: 3px 8px;
            }
            QPushButton:hover { background-color: #0b7dda; }
            QPushButton:disabled { background-color: #cccccc; color: #666666; }
        """)
        folder_button.clicked.connect(self.open_folder)
        buttons_layout.addWidget(folder_button)
        
        # Add Delete button
        delete_button = QPushButton("🗑️")
        delete_button.setToolTip("Xóa khỏi danh sách")
        delete_button.setFixedHeight(30)
        delete_button.setFixedWidth(40)
        delete_button.setCursor(Qt.PointingHandCursor)
        delete_button.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border-radius: 4px;
                padding: 3px 6px;
            }
            QPushButton:hover { background-color: #d32f2f; }
        """)
        delete_button.clicked.connect(self.remove_download)
        buttons_layout.addWidget(delete_button)
        
        layout.addWidget(buttons_widget)
        
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-radius: 6px;
            }
        """)
        self.setMinimumHeight(80)
        self.setMaximumHeight(80)
        
    def open_file(self):
        """Open the downloaded file with improved error handling"""
        if not self.output_file:
            QMessageBox.warning(self, "Không có file", "Không có thông tin về file để mở.")
            return
            
        if not os.path.exists(self.output_file):
            # Check if the file exists in a different location
            file_name = os.path.basename(self.output_file)
            alternative_locations = [
                os.path.join(os.path.expanduser("~/Downloads"), file_name),
                os.path.join(os.path.expanduser("~/Desktop"), file_name),
                os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), file_name)
            ]
            
            found_file = None
            for location in alternative_locations:
                if os.path.exists(location):
                    found_file = location
                    break
                    
            if found_file:
                # Update the path in the download manager
                if hasattr(self, 'download_id'):
                    download_manager = DownloadManager.get_instance()
                    download_info = download_manager.get_download(self.download_id)
                    if download_info:
                        download_info.output_file = found_file
                        download_manager.save_downloads()
                
                self.output_file = found_file
                QMessageBox.information(self, "Đã tìm thấy file", f"Đã tìm thấy file ở vị trí khác: {found_file}")
            else:
                QMessageBox.warning(self, "Không tìm thấy file", 
                    f"Không thể tìm thấy file: {self.output_file}\n\nFile có thể đã bị di chuyển hoặc xoá.")
                return
        
        try:
            if self.parent_menu:
                self.parent_menu.open_file(self.output_file)
            else:
                try:
                    if os.name == 'nt':  # Windows
                        os.startfile(self.output_file)
                    elif os.name == 'posix':  # macOS, Linux
                        subprocess.run(['xdg-open', self.output_file])
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Không thể mở file: {str(e)}")
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể mở file: {str(e)}")
    
    def open_folder(self):
        """Open the folder containing the downloaded file with improved error handling"""
        if not self.output_file:
            QMessageBox.warning(self, "Không có thông tin", "Không có thông tin về đường dẫn file.")
            return
            
        folder_path = os.path.dirname(self.output_file)
        if not os.path.exists(folder_path):
            QMessageBox.warning(self, "Không tìm thấy thư mục", 
                f"Không thể tìm thấy thư mục: {folder_path}\n\nThư mục có thể đã bị di chuyển hoặc xoá.")
            return
            
        try:
            if self.parent_menu:
                self.parent_menu.open_folder(folder_path)
            else:
                try:
                    if os.name == 'nt':  # Windows
                        os.startfile(folder_path)
                    elif os.name == 'posix':  # macOS, Linux
                        subprocess.run(['xdg-open', folder_path])
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Không thể mở thư mục: {str(e)}")
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể mở thư mục: {str(e)}")
    
    def remove_download(self):
        """Robust download removal that works with any widget structure"""
        try:
            # First remove from the download manager
            download_manager = DownloadManager.get_instance()
            download_manager.remove_download(self.download_id)
            
            # Method 1: Try to find and remove this widget directly from the list
            parent_list = self.parent()
            if isinstance(parent_list, QListWidget):
                for i in range(parent_list.count()):
                    item = parent_list.item(i)
                    if parent_list.itemWidget(item) == self:
                        parent_list.takeItem(i)
                        print(f"Successfully removed item at index {i} from list")
                        return True
                
            # Method 2: If we couldn't remove the item directly, try using our stored list_widget
            if self.list_widget is not None and isinstance(self.list_widget, QListWidget):
                for i in range(self.list_widget.count()):
                    item = self.list_widget.item(i)
                    if self.list_widget.itemWidget(item) == self:
                        self.list_widget.takeItem(i)
                        print(f"Successfully removed item at index {i} from stored list")
                        return True
            
            # Method 3: Fall back to refreshing the parent window's list
            if self.parent_menu and hasattr(self.parent_menu, 'update_download_status'):
                print("Falling back to refreshing the download status")
                self.parent_menu.update_download_status()
                return True
            
            return True
            
        except Exception as e:
            print(f"Error removing download item: {str(e)}")
            
            # Last resort: force a refresh using timer
            try:
                if self.parent_menu and hasattr(self.parent_menu, 'update_download_status'):
                    print("Using timer to refresh the list after error")
                    QTimer.singleShot(100, self.parent_menu.update_download_status)
            except Exception as e2:
                print(f"Final fallback also failed: {str(e2)}")
                
            return False

class MainMenu(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KHyTool - Main Menu")
        self.setMinimumSize(900, 650)
        self.initUI()
        
        self.showMaximized()
        
        self.download_timer = QTimer(self)
        self.download_timer.timeout.connect(self.update_download_status)
        self.download_timer.start(1000)
        
        self.download_manager = DownloadManager.get_instance()
        self.download_thumbnails = {}

    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor("#ffffff"))
        self.setPalette(palette)
        
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(5, 0, 5, 0)
        header_widget.setStyleSheet("background-color: transparent;")

        left_sticker = QLabel("🗂️")
        left_sticker.setFont(QFont("Segoe UI Emoji", 32))
        left_sticker.setAlignment(Qt.AlignCenter)
        left_sticker.setStyleSheet("background-color: transparent;")
        header_layout.addWidget(left_sticker)

        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(5)

        title_label = QLabel("Quản lý dự án")
        title_label.setFont(QFont("Arial", 28, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            color: #4CAF50;
            background-color: transparent;
        """)
        title_layout.addWidget(title_label)

        subtitle_label = QLabel("Tổ chức và quản lý video, ảnh, âm thanh và phụ đề")
        subtitle_label.setFont(QFont("Arial", 14))
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #555; background-color: transparent;")
        title_layout.addWidget(subtitle_label)

        header_layout.addWidget(title_container, 1)

        right_sticker = QLabel("🎬")
        right_sticker.setFont(QFont("Segoe UI Emoji", 32))
        right_sticker.setAlignment(Qt.AlignCenter)
        right_sticker.setStyleSheet("background-color: transparent;")
        header_layout.addWidget(right_sticker)

        main_layout.addWidget(header_widget)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #2E7D32; min-height: 2px;")
        main_layout.addWidget(separator)
        
        features_container = QWidget()
        features_main_layout = QVBoxLayout(features_container)
        features_main_layout.setSpacing(20)
        features_main_layout.setContentsMargins(0, 0, 0, 0)
        
        project_card = self.create_feature_card(
            title="QUẢN LÝ DỰ ÁN", 
            description="Tổ chức và quản lý video, ảnh, âm thanh và phụ đề cho các dự án của bạn.",
            emoji="🗂️",
            primary=True,
            color="#2E7D32",
            handler=self.open_project_manager,
            button_text="🚀 MỞ QUẢN LÝ DỰ ÁN"
        )
        features_main_layout.addWidget(project_card)
        
        downloaders_card = QFrame()
        downloaders_card.setObjectName("downloadersCard")
        
        downloaders_card.setStyleSheet("""
            #downloadersCard {
                background-color: #f8f8f8;
                border: 2px solid #1976D2;
                border-radius: 15px;
                padding: 15px;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect(downloaders_card)
        shadow.setBlurRadius(15)
        shadow.setXOffset(3)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 60))
        downloaders_card.setGraphicsEffect(shadow)
        
        downloaders_layout = QVBoxLayout(downloaders_card)
        downloaders_layout.setSpacing(15)
        
        download_header = QHBoxLayout()
        download_emoji = QLabel("📥")
        download_emoji.setFont(QFont("Segoe UI Emoji", 22))
        download_title = QLabel("TẢI VIDEO")
        download_title.setFont(QFont("Arial", 16, QFont.Bold))
        download_title.setStyleSheet("color: #1976D2;")
        
        download_header.addWidget(download_emoji)
        download_header.addWidget(download_title)
        download_header.addStretch(1)
        downloaders_layout.addLayout(download_header)
        
        download_desc = QLabel("Tải video từ các nền tảng phổ biến với chất lượng cao")
        download_desc.setWordWrap(True)
        download_desc.setStyleSheet("color: #555; font-size: 20px;")
        downloaders_layout.addWidget(download_desc)
        
        download_buttons_layout = QHBoxLayout()
        download_buttons_layout.setSpacing(15)
        
        youtube_btn = QPushButton("TẢI VIDEO YOUTUBE")
        youtube_btn.setMinimumHeight(60)
        youtube_btn.setFont(QFont("Arial", 12, QFont.Bold))
        youtube_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF0000;
                color: white;
                border-radius: 8px;
                padding: 12px;
                text-align: center;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
        """)
        youtube_btn.clicked.connect(self.open_youtube_downloader)
        download_buttons_layout.addWidget(youtube_btn)
        
        tiktok_btn = QPushButton("TẢI VIDEO TIKTOK")
        tiktok_btn.setMinimumHeight(60)
        tiktok_btn.setFont(QFont("Arial", 12, QFont.Bold))
        tiktok_btn.setStyleSheet("""
            QPushButton {
                background-color: #000000;
                color: white;
                border-radius: 8px;
                padding: 12px;
                text-align: center;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #333333;
            }
        """)
        tiktok_btn.clicked.connect(self.open_tiktok_downloader)
        download_buttons_layout.addWidget(tiktok_btn)
        
        facebook_btn = QPushButton("TẢI VIDEO FACEBOOK")
        facebook_btn.setMinimumHeight(60)
        facebook_btn.setFont(QFont("Arial", 12, QFont.Bold))
        facebook_btn.setStyleSheet("""
            QPushButton {
                background-color: #1877F2;
                color: white;
                border-radius: 8px;
                padding: 12px;
                text-align: center;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0D5EB8;
            }
        """)
        facebook_btn.clicked.connect(self.open_facebook_downloader)
        download_buttons_layout.addWidget(facebook_btn)
        
        downloaders_layout.addLayout(download_buttons_layout)
        
        features_main_layout.addWidget(downloaders_card)
        
        main_layout.addWidget(features_container)
        
        downloads_widget = QWidget()
        downloads_widget.setMaximumHeight(300)  # Reduced from unlimited to 300px
        downloads_layout = QVBoxLayout(downloads_widget)
        downloads_layout.setContentsMargins(0, 0, 0, 0)
        
        downloads_group = QGroupBox("Tải Xuống Trong Nền")
        downloads_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 8px;
                margin-top: 12px;
                background-color: #ffffff;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
                color: #2196F3;
                background-color: #ffffff;
                font-size: 14px;
            }
        """)
        
        downloads_inner_layout = QVBoxLayout()
        downloads_inner_layout.setSpacing(6)
        
        download_header = QHBoxLayout()
        download_status_icon = QLabel("📥")
        download_status_icon.setFont(QFont("Segoe UI Emoji", 16))
        download_status_title = QLabel("Danh sách tải xuống")
        download_status_title.setFont(QFont("Arial", 12, QFont.Bold))
        download_status_title.setStyleSheet("color: #2196F3;")
        
        download_header.addWidget(download_status_icon)
        download_status_title.setVisible(True)
        download_header.addWidget(download_status_title)
        download_header.addStretch(1)
        
        view_all_btn = QPushButton("Xem tất cả")
        view_all_btn.setCursor(Qt.PointingHandCursor)
        view_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 4px;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        view_all_btn.clicked.connect(self.open_download_manager_window)
        download_header.addWidget(view_all_btn)
        
        downloads_inner_layout.addLayout(download_header)
        
        self.downloads_list = QListWidget()
        self.downloads_list.setAlternatingRowColors(True)
        self.downloads_list.setStyleSheet("""
            QListWidget {
                background-color: #f9f9f9;
                border-radius: 4px;
                border: 1px solid #e0e0e0;
                padding: 5px;
            }
            QListWidget::item {
                background-color: white;
                margin: 5px;
                border-radius: 6px;
                border: 1px solid #e0e0e0;
            }
        """)
        self.downloads_list.setIconSize(QSize(120, 68))
        self.downloads_list.setUniformItemSizes(False)
        self.downloads_list.setWordWrap(True)
        
        self.no_downloads_label = QLabel("Không có tác vụ tải xuống nào")
        self.no_downloads_label.setAlignment(Qt.AlignCenter)
        self.no_downloads_label.setStyleSheet("color: #888; font-style: italic; padding: 20px;")
        downloads_inner_layout.addWidget(self.no_downloads_label)
        
        self.downloads_list.setMinimumHeight(170)
        self.downloads_list.setMaximumHeight(170)
        downloads_inner_layout.addWidget(self.downloads_list)
        
        downloads_group.setLayout(downloads_inner_layout)
        downloads_layout.addWidget(downloads_group)
        
        main_layout.addWidget(downloads_widget)
        
        footer_widget = QWidget()
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 10, 0, 0)
        
        for emoji in ["⭐", "🚀", "🎯"]:
            emoji_label = QLabel(emoji)
            emoji_label.setFont(QFont("Segoe UI Emoji", 16))
            footer_layout.addWidget(emoji_label)
        
        footer_layout.addStretch(1)
        
        footer_label = QLabel("🛠️ KHyTool v1.0 © 2025")
        footer_label.setFont(QFont("Arial", 10))
        footer_label.setStyleSheet("color: #888;")
        footer_layout.addWidget(footer_label)
        
        footer_layout.addStretch(1)
        
        for emoji in ["💡", "🎬", "🔍"]:
            emoji_label = QLabel(emoji)
            emoji_label.setFont(QFont("Segoe UI Emoji", 16))
            footer_layout.addWidget(emoji_label)
        
        main_layout.addWidget(footer_widget)
        
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #ffffff;
                font-family: 'Arial', sans-serif;
            }
            QPushButton {
                min-height: 40px;
                font-size: 14px;
            }
            QLabel {
                color: #333;
                background-color: transparent;
            }
            QGroupBox {
                background-color: #ffffff;
            }
        """)

    def create_feature_card(self, title, description, emoji, primary, color, handler, button_text):
        card = QFrame()
        
        card.setObjectName("featureCard")
        
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(15)
        shadow.setXOffset(3)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 60))
        card.setGraphicsEffect(shadow)
        
        bg_color = "#ffffff"
        border_color = color
        
        if primary:
            bg_color = "#ffffff"
            
        card.setStyleSheet(f"""
            #featureCard {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 15px;
                padding: 15px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title_layout = QHBoxLayout()
        
        emoji_label = QLabel(emoji)
        emoji_label.setFont(QFont("Segoe UI Emoji", 24))
        emoji_label.setStyleSheet("background-color: transparent;")
        title_layout.addWidget(emoji_label)
        
        title_label = QLabel(title)
        font_size = 18 if primary else 16
        title_font = QFont("Arial", font_size, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {color}; background-color: transparent;")
        title_layout.addWidget(title_label, 1)
        
        layout.addLayout(title_layout)
        
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #333; font-size: 20px; background-color: transparent;")
        desc_label.setMinimumHeight(50)
        layout.addWidget(desc_label)
        
        layout.addStretch(1)
        
        button = QPushButton(button_text)
        button_height = 50 if primary else 40
        button_font_size = 13 if primary else 12
        button.setMinimumHeight(button_height)
        button.setFont(QFont("Arial", button_font_size, QFont.Bold))
        
        hover_color = self.lighten_color(color, 1.2)
        
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border-radius: 8px;
                padding: 8px 15px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
        """)
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(handler)
        
        layout.addWidget(button)
        
        return card
    
    def lighten_color(self, color_hex, factor=1.2):
        color = QColor(color_hex)
        h, s, v, _ = color.getHslF()
        
        v = min(v * factor, 1.0)
        
        color.setHslF(h, s, v, 1.0)
        return color.name()

    def update_download_status(self):
        """Update download status in the UI with improved error handling"""
        try:
            # Clear current list
            self.downloads_list.clear()
            
            # Get all downloads
            downloads = self.download_manager.get_all_downloads()
            
            # Check if we have any downloads
            if not downloads:
                self.no_downloads_label.setVisible(True)
                self.downloads_list.setVisible(False)
                return
            else:
                self.no_downloads_label.setVisible(False)
                self.downloads_list.setVisible(True)
            
            # Sort downloads: active first, then completed, then others
            # Also limit to 2 recent downloads for the main view (reduced from 5)
            sorted_downloads = []
            
            # Use safer filtering with isinstance and hasattr checks
            active_downloads = []
            completed_downloads = []
            other_downloads = []
            
            for d in downloads:
                if not hasattr(d, 'status'):
                    other_downloads.append(d)
                    continue
                    
                if d.status in ['downloading', 'processing']:
                    active_downloads.append(d)
                elif d.status == 'completed':
                    completed_downloads.append(d)
                else:
                    other_downloads.append(d)
            
            # Sort each category by timestamp (newest first) with safer access
            for download_list in [active_downloads, completed_downloads, other_downloads]:
                try:
                    download_list.sort(
                        key=lambda d: getattr(d, 'timestamp', 0) if hasattr(d, 'timestamp') else 0, 
                        reverse=True
                    )
                except Exception as e:
                    print(f"Error sorting downloads: {str(e)}")
            
            # Combine the lists
            sorted_downloads = active_downloads + completed_downloads + other_downloads
            
            # Show only 2 most recent downloads in the main view
            recent_downloads = sorted_downloads[:2]
            
            # Add each download as a custom widget with improved error handling
            for download in recent_downloads:
                try:
                    if not hasattr(download, 'id'):
                        continue
                        
                    item = QListWidgetItem(self.downloads_list)
                    
                    # Create custom widget for the item
                    widget = DownloadItemWidget(
                        download.id,
                        download.title,
                        download.status,
                        download.thumbnail_path if hasattr(download, 'thumbnail_path') else None,
                        download.progress if hasattr(download, 'progress') else 0,
                        download.output_file if hasattr(download, 'output_file') else None,
                        self
                    )
                    
                    # Add this line to set the list_widget reference
                    widget.list_widget = self.downloads_list
                    
                    item.setSizeHint(widget.sizeHint())
                    self.downloads_list.addItem(item)
                    self.downloads_list.setItemWidget(item, widget)
                except Exception as e:
                    print(f"Error adding download item to list: {str(e)}")
        except Exception as e:
            print(f"Error updating download status: {str(e)}")
    
    def open_download_manager_window(self):
        """Open standalone download manager window"""
        from ui.download_manager_window import DownloadManagerWindow
        self.download_manager_window = DownloadManagerWindow(self)
        self.download_manager_window.show()
    
    def open_file(self, file_path):
        try:
            if os.path.exists(file_path):
                if os.name == 'nt':
                    os.startfile(file_path)
                elif os.name == 'posix':
                    subprocess.Popen(['xdg-open', file_path])
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể mở file: {str(e)}")
    
    def open_folder(self, folder_path):
        try:
            if os.path.exists(folder_path):
                if os.name == 'nt':
                    os.startfile(folder_path)
                elif os.name == 'posix':
                    subprocess.Popen(['xdg-open', folder_path])
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể mở thư mục: {str(e)}")

    def open_project_manager(self):
        self.project_manager_window = ProjectManagerWindow()
        self.project_manager_window.show()
        self.close()

    def open_youtube_downloader(self):
        self.youtube_window = YouTubeDownloaderWindow()
        self.youtube_window.show()
        self.close()

    def open_tiktok_downloader(self):
        self.tiktok_window = TikTokDownloaderWindow()
        self.tiktok_window.show()
        self.close()

    def open_facebook_downloader(self):
        self.facebook_window = FacebookDownloaderWindow()
        self.facebook_window.show()
        self.close()

    def closeEvent(self, event):
        # Save downloads before closing
        self.download_manager.save_downloads()
        event.accept()
