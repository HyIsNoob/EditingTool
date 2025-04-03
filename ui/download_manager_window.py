from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, QMessageBox,
                             QFrame, QProgressBar, QFileDialog)
from PyQt5.QtGui import QFont, QPixmap, QIcon
from PyQt5.QtCore import Qt, QSize, QTimer
import os
import sys
import subprocess
from utils.download_manager import DownloadManager

class DownloadItemWidget(QWidget):
    """Custom widget for download list items with buttons"""
    
    def __init__(self, download_id, title, status, thumbnail_path, progress, output_file, list_widget=None, parent_window=None):
        super().__init__()
        self.download_id = download_id
        self.output_file = output_file
        self.list_widget = list_widget  # Store reference to the list widget
        self.parent_window = parent_window  # Store reference to the parent window
        
        # Setup layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Thumbnail (left side)
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(120, 68)  # 16:9 aspect ratio
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
        
        # Progress bar or status
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
            status_text = "✅ Hoàn tất" if status == 'completed' else "❌ Lỗi" if status == 'error' else "⏸️ Đã dừng"
            status_label = QLabel(status_text)
            status_label.setStyleSheet("color: #666;")
            info_layout.addWidget(status_label)
        
        layout.addWidget(info_widget, 1)  # 1 means this widget will take available space
        
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
        delete_button = QPushButton("🗑️ Xóa")
        delete_button.setToolTip("Xóa khỏi danh sách")
        delete_button.setFixedHeight(30)
        delete_button.setCursor(Qt.PointingHandCursor)
        delete_button.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border-radius: 4px;
                padding: 3px 8px;
            }
            QPushButton:hover { background-color: #d32f2f; }
        """)
        delete_button.clicked.connect(self.remove_download)
        buttons_layout.addWidget(delete_button)
        
        layout.addWidget(buttons_widget)
        
        # Set overall style
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-radius: 6px;
            }
        """)
        self.setMinimumHeight(80)
        self.setMaximumHeight(80)
        
    def open_file(self):
        if self.output_file and os.path.exists(self.output_file):
            if self.parent_window:
                self.parent_window.open_file(self.output_file)
            else:
                try:
                    if os.name == 'nt':  # Windows
                        os.startfile(self.output_file)
                    elif os.name == 'posix':  # macOS, Linux
                        subprocess.run(['xdg-open', self.output_file])
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Không thể mở file: {str(e)}")
        else:
            QMessageBox.warning(self, "Không tìm thấy file", "Không thể tìm thấy file đã tải.")
    
    def open_folder(self):
        if self.output_file and os.path.exists(self.output_file):
            folder_path = os.path.dirname(self.output_file)
            if self.parent_window:
                self.parent_window.open_folder(folder_path)
            else:
                try:
                    if os.name == 'nt':  # Windows
                        os.startfile(folder_path)
                    elif os.name == 'posix':  # macOS, Linux
                        subprocess.run(['xdg-open', folder_path])
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Không thể mở thư mục: {str(e)}")
        else:
            QMessageBox.warning(self, "Không tìm thấy thư mục", "Không thể tìm thấy thư mục chứa file.")
    
    def remove_download(self):
        """Robust download removal that works with any widget structure"""
        try:
            # First remove from the download manager
            download_manager = DownloadManager.get_instance()
            download_manager.remove_download(self.download_id)
            
            # Method 1: Try to find and remove this widget directly from the list
            if self.list_widget is not None:
                # Use isinstance to explicitly check if it's a QListWidget
                if isinstance(self.list_widget, QListWidget):
                    for i in range(self.list_widget.count()):
                        item = self.list_widget.item(i)
                        if self.list_widget.itemWidget(item) == self:
                            self.list_widget.takeItem(i)
                            print(f"Successfully removed item at index {i} from list")
                            return True
                else:
                    print(f"Warning: list_widget is not a QListWidget: {type(self.list_widget)}")
            
            # Method 2: If we couldn't remove the item directly, fall back to refreshing the whole list
            print("Falling back to refreshing the parent window's list")
            if self.parent_window and hasattr(self.parent_window, 'refresh_download_list'):
                self.parent_window.refresh_download_list()
                return True
            else:
                print("Warning: Cannot refresh parent window list")
                
            return True
            
        except Exception as e:
            print(f"Error removing download item: {str(e)}")
            
            # Last resort: force a refresh of the parent window's list
            try:
                if self.parent_window and hasattr(self.parent_window, 'refresh_download_list'):
                    print("Using timer to refresh the list after error")
                    QTimer.singleShot(100, self.parent_window.refresh_download_list)
            except Exception as e2:
                print(f"Final fallback also failed: {str(e2)}")
                
            return False


class DownloadManagerWindow(QMainWindow):
    """Standalone window for managing all downloads"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("KHyTool - Quản Lý Tải Xuống")
        self.resize(1000, 700)  # Larger size for standalone window
        self.download_manager = DownloadManager.get_instance()
        self.parent_menu = parent
        self.initUI()
        
        # Update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_download_list)
        self.update_timer.start(1000)  # Update every second
    
    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        header_label = QLabel("Quản lý tải xuống")
        header_label.setFont(QFont("Arial", 24, QFont.Bold))
        header_label.setStyleSheet("color: #2196F3;")
        header_layout.addWidget(header_label)
        
        refresh_btn = QPushButton("🔄 Làm mới")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #0b7dda; }
        """)
        refresh_btn.clicked.connect(self.update_download_list)
        header_layout.addWidget(refresh_btn)
        
        layout.addWidget(header_widget)
        
        # Filter options
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        
        filter_label = QLabel("Lọc:")
        filter_label.setStyleSheet("font-weight: bold;")
        filter_layout.addWidget(filter_label)
        
        self.filter_all = QPushButton("Tất cả")
        self.filter_all.setCheckable(True)
        self.filter_all.setChecked(True)
        self.filter_all.clicked.connect(lambda: self.set_filter("all"))
        
        self.filter_completed = QPushButton("Hoàn thành")
        self.filter_completed.setCheckable(True)
        self.filter_completed.clicked.connect(lambda: self.set_filter("completed"))
        
        self.filter_in_progress = QPushButton("Đang tải")
        self.filter_in_progress.setCheckable(True)
        self.filter_in_progress.clicked.connect(lambda: self.set_filter("in_progress"))
        
        self.filter_error = QPushButton("Lỗi")
        self.filter_error.setCheckable(True)
        self.filter_error.clicked.connect(lambda: self.set_filter("error"))
        
        filter_btn_style = """
            QPushButton {
                background-color: #f0f0f0;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:checked {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover:!checked {
                background-color: #e0e0e0;
            }
        """
        
        self.filter_all.setStyleSheet(filter_btn_style)
        self.filter_completed.setStyleSheet(filter_btn_style)
        self.filter_in_progress.setStyleSheet(filter_btn_style)
        self.filter_error.setStyleSheet(filter_btn_style)
        
        filter_layout.addWidget(self.filter_all)
        filter_layout.addWidget(self.filter_completed)
        filter_layout.addWidget(self.filter_in_progress)
        filter_layout.addWidget(self.filter_error)
        filter_layout.addStretch(1)
        
        # Add clear all button
        clear_all_btn = QPushButton("🗑️ Xóa tất cả")
        clear_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border-radius: 4px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #d32f2f; }
        """)
        clear_all_btn.clicked.connect(self.clear_all_downloads)
        filter_layout.addWidget(clear_all_btn)
        
        layout.addLayout(filter_layout)
        
        # Download list
        self.download_list = QListWidget()
        self.download_list.setStyleSheet("""
            QListWidget {
                background-color: #f9f9f9;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 5px;
            }
            QListWidget::item {
                background-color: white;
                margin: 5px;
                border-radius: 6px;
                border: 1px solid #e0e0e0;
            }
        """)
        self.download_list.setMinimumHeight(500)  # Lots of space for downloads
        self.download_list.setSelectionMode(QListWidget.NoSelection)
        self.download_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        
        layout.addWidget(self.download_list)
        
        # No downloads message
        self.no_downloads_label = QLabel("Không có tệp tải xuống nào")
        self.no_downloads_label.setAlignment(Qt.AlignCenter)
        self.no_downloads_label.setStyleSheet("color: #888; font-style: italic; padding: 20px; font-size: 16px;")
        layout.addWidget(self.no_downloads_label)
        self.no_downloads_label.hide()
        
        # Back button at the bottom
        back_button = QPushButton("Quay lại")
        back_button.setStyleSheet("""
            QPushButton {
                background-color: #555;
                color: white;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #333; }
        """)
        back_button.clicked.connect(self.close)
        
        layout.addWidget(back_button)
        
        self.current_filter = "all"
        self.update_download_list()
    
    def set_filter(self, filter_type):
        # Update button states
        self.filter_all.setChecked(filter_type == "all")
        self.filter_completed.setChecked(filter_type == "completed")
        self.filter_in_progress.setChecked(filter_type == "in_progress")
        self.filter_error.setChecked(filter_type == "error")
        
        # Save the filter
        self.current_filter = filter_type
        
        # Refresh the list
        self.update_download_list()
    
    def update_download_list(self):
        """Update the download list with current downloads"""
        self.refresh_download_list()
    
    def refresh_download_list(self):
        """Refresh the download list with improved error handling"""
        try:
            # Clear the list
            self.download_list.clear()
            
            # Get all downloads
            downloads = self.download_manager.get_all_downloads()
            if not downloads:
                self.no_downloads_label.show()
                return
            
            # Filter downloads based on current filter with safer checks
            filtered_downloads = []
            
            if self.current_filter == "all":
                filtered_downloads = downloads
            else:
                for d in downloads:
                    if not hasattr(d, 'status'):
                        continue
                        
                    if self.current_filter == "completed" and d.status == 'completed':
                        filtered_downloads.append(d)
                    elif self.current_filter == "in_progress" and d.status in ['downloading', 'processing', 'paused', 'running']:
                        filtered_downloads.append(d)
                    elif self.current_filter == "error" and d.status == 'error':
                        filtered_downloads.append(d)
            
            # Sort downloads by timestamp (newest first) with safer approach
            try:
                filtered_downloads.sort(
                    key=lambda d: getattr(d, 'timestamp', 0) if hasattr(d, 'timestamp') else 0,
                    reverse=True
                )
            except Exception as e:
                print(f"Error sorting downloads: {str(e)}")
            
            # Show "no downloads" message if needed
            if not filtered_downloads:
                self.no_downloads_label.show()
                return
            else:
                self.no_downloads_label.hide()
            
            # Add each download as a custom widget with improved error handling
            for download in filtered_downloads:
                try:
                    if not hasattr(download, 'id') or not download.id:
                        continue
                        
                    item = QListWidgetItem(self.download_list)
                    
                    # Create custom widget for the item with safer attribute access and proper references
                    widget = DownloadItemWidget(
                        download.id,
                        getattr(download, 'title', 'Unknown'),
                        getattr(download, 'status', 'unknown'),
                        getattr(download, 'thumbnail_path', None),
                        getattr(download, 'progress', 0),
                        getattr(download, 'output_file', None),
                        self.download_list,  # Pass reference to the list widget
                        self  # Pass reference to parent window
                    )
                    
                    item.setSizeHint(widget.sizeHint())
                    self.download_list.addItem(item)
                    self.download_list.setItemWidget(item, widget)
                except Exception as e:
                    print(f"Error adding download item to list: {str(e)}")
        except Exception as e:
            print(f"Error refreshing download list: {str(e)}")
            self.no_downloads_label.show()
    
    def clear_all_downloads(self):
        """Clear all downloads from the list"""
        reply = QMessageBox.question(
            self, 
            "Xác nhận xóa tất cả", 
            "Bạn có chắc muốn xóa tất cả mục khỏi danh sách tải xuống?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Get current filtered downloads
            downloads = self.download_manager.get_all_downloads()
            
            if self.current_filter != "all":
                if self.current_filter == "completed":
                    downloads = [d for d in downloads if hasattr(d, 'status') and d.status == 'completed']
                elif self.current_filter == "in_progress":
                    downloads = [d for d in downloads if hasattr(d, 'status') and d.status in ['downloading', 'processing', 'paused']]
                elif self.current_filter == "error":
                    downloads = [d for d in downloads if hasattr(d, 'status') and d.status == 'error']
            
            # Remove each download
            for download in downloads:
                if hasattr(download, 'id'):
                    self.download_manager.remove_download(download.id)
            
            # Refresh the list
            self.refresh_download_list()
    
    def open_file(self, file_path):
        """Open the file with default application"""
        try:
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            elif os.name == 'posix':  # macOS, Linux
                subprocess.run(['xdg-open', file_path])
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể mở file: {str(e)}")
    
    def open_folder(self, folder_path):
        """Open the folder containing the file"""
        try:
            if os.name == 'nt':  # Windows
                os.startfile(folder_path)
            elif os.name == 'posix':  # macOS, Linux
                subprocess.run(['xdg-open', folder_path])
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể mở thư mục: {str(e)}")
