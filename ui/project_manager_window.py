from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTabWidget, QListWidget, QListWidgetItem, QFileDialog,
                             QMessageBox, QGroupBox, QSplitter, QMenu, QAction, QInputDialog, QCheckBox)
from PyQt5.QtCore import Qt, QSize, QMimeData, QUrl, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon, QFont, QDrag
import os
from project.manager import ProjectManager
import json

class DragDropFileList(QListWidget):
    """Widget danh sách file hỗ trợ kéo thả"""
    
    files_dropped = pyqtSignal(list, str)  # file_paths, folder_name
    
    def __init__(self, folder_name, parent=None):
        super().__init__(parent)
        self.folder_name = folder_name
        self.setAcceptDrops(True)
        self.setIconSize(QSize(36, 36))
        self.setSelectionMode(QListWidget.ExtendedSelection)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            file_paths = [url.toLocalFile() for url in event.mimeData().urls() if os.path.isfile(url.toLocalFile())]
            if file_paths:
                self.files_dropped.emit(file_paths, self.folder_name)
        else:
            event.ignore()

class ProjectManagerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KHyTool - Quản lý dự án")
        self.setMinimumSize(1000, 700)
        self.showMaximized()  # Đảm bảo mở full screen
        self.project_manager = ProjectManager()
        self.current_project = None
        self.current_folder = None
        self.auto_refresh = True  # Enable auto-refresh by default
        self.auto_organize = True  # Enable auto-organize by default
        self.refresh_timer = None
        self.initUI()
        self.load_projects()
        
        # Tự động mở dự án gần nhất nếu có
        last_project = self.project_manager.current_project
        if last_project and os.path.exists(last_project):
            try:
                self.open_project_from_path(last_project)
            except:
                pass  # Nếu không mở được thì bỏ qua
        
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #f5f5f5;
                color: #333;
                font-family: Arial, sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 6px;
                margin-top: 12px;
                background-color: #ffffff;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #4CAF50;
                background-color: transparent;
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
            }
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #f5f5f5;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #eee;
                background-color: transparent;
            }
            QListWidget::item:selected {
                background-color: #e8f5e9;
                color: #2e7d32;
            }
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #f5f5f5;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                border: 1px solid #e0e0e0;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #4CAF50;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background-color: #e8f5e9;
            }
            QLabel {
                background-color: transparent;
            }
            QLineEdit, QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 4px;
            }
            QStatusBar {
                background-color: #f5f5f5;
            }
        """)

    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)  # Tăng spacing cho không gian thở

        # Header với thiết kế hiện đại hơn
        header_widget = QWidget()
        header_widget.setStyleSheet("background-color: #e8f5e9; border-radius: 8px;")
        header_layout = QHBoxLayout(header_widget)
        
        header_icon = QLabel()
        header_icon.setPixmap(QIcon("resources/icons/project_manager.png").pixmap(QSize(48, 48)))
        header_layout.addWidget(header_icon)
        
        header_label = QLabel("Quản Lý Dự Án Video")
        header_label.setFont(QFont("Arial", 20, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setStyleSheet("color: #2e7d32; margin: 10px 0;")
        header_layout.addWidget(header_label, 1)
        
        main_layout.addWidget(header_widget)

        # Splitter
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setHandleWidth(8)  # Tăng độ rộng của handle để dễ kéo hơn
        main_splitter.setStyleSheet("QSplitter::handle {background-color: #e0e0e0; border-radius: 4px;}")

        # Left Panel: Project List - Với thiết kế card
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # Card cho thư mục cơ sở
        base_dir_group = QGroupBox("Thư Mục Lưu Dự Án")
        base_dir_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 8px;
                margin-top: 8px;  /* Điều chỉnh lên cao hơn */
                background-color: #ffffff;
                padding: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
                color: #2e7d32;
                background-color: #ffffff;  /* Thêm nền trắng cho tiêu đề */
            }
        """)
        
        base_dir_layout = QHBoxLayout(base_dir_group)
        
        self.base_dir_label = QLabel(self.project_manager.base_dir)
        self.base_dir_label.setStyleSheet("font-style: italic; color: #666; padding: 5px;")
        self.base_dir_label.setWordWrap(True)
        
        change_base_dir_btn = QPushButton("Thay Đổi")
        change_base_dir_btn.setIcon(QIcon("resources/icons/folder.png"))
        change_base_dir_btn.setIconSize(QSize(18, 18))
        change_base_dir_btn.clicked.connect(self.change_base_directory)
        change_base_dir_btn.setCursor(Qt.PointingHandCursor)
        
        base_dir_layout.addWidget(self.base_dir_label, 1)
        base_dir_layout.addWidget(change_base_dir_btn)
        
        left_layout.addWidget(base_dir_group)

        # Card cho danh sách dự án
        project_group = QGroupBox("Dự Án Của Tôi")
        project_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 8px;
                margin-top: 12px;
                background-color: #ffffff;
                padding: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
                color: #2e7d32;
                background-color: transparent;
            }
        """)
        
        project_layout = QVBoxLayout(project_group)
        project_layout.setSpacing(10)

        # Các nút tạo và mở dự án với thiết kế đẹp hơn
        button_layout = QHBoxLayout()
        
        new_project_btn = QPushButton("Tạo Dự Án Mới")
        new_project_btn.setIcon(QIcon("resources/icons/add.png"))
        new_project_btn.setIconSize(QSize(20, 20))
        new_project_btn.setStyleSheet("""
            QPushButton { 
                text-align: left; 
                padding: 10px 15px; 
                font-weight: bold;
                border-radius: 6px;
            }
        """)
        new_project_btn.clicked.connect(self.create_project)
        new_project_btn.setCursor(Qt.PointingHandCursor)
        
        open_project_btn = QPushButton("Mở Thư Mục")
        open_project_btn.setIcon(QIcon("resources/icons/folder.png"))
        open_project_btn.setIconSize(QSize(20, 20))
        open_project_btn.setStyleSheet("""
            QPushButton { 
                text-align: left; 
                padding: 10px 15px; 
                font-weight: bold;
                border-radius: 6px;
            }
        """)
        open_project_btn.clicked.connect(self.select_project_folder)
        open_project_btn.setCursor(Qt.PointingHandCursor)
        
        button_layout.addWidget(new_project_btn)
        button_layout.addWidget(open_project_btn)
        project_layout.addLayout(button_layout)

        # Tiêu đề danh sách dự án
        project_header = QWidget()
        project_header_layout = QHBoxLayout(project_header)
        project_header_layout.setContentsMargins(0, 5, 0, 5)
        
        project_label = QLabel("Dự án gần đây:")
        project_label.setStyleSheet("font-weight: bold; color: #555;")
        project_header_layout.addWidget(project_label)

        # Thêm nút làm mới danh sách dự án
        refresh_projects_btn = QPushButton("Làm mới")
        refresh_projects_btn.setFixedSize(80, 28)  # Điều chỉnh kích thước cho phù hợp với text
        refresh_projects_btn.setToolTip("Làm mới danh sách dự án")
        refresh_projects_btn.clicked.connect(self.load_projects)
        refresh_projects_btn.setCursor(Qt.PointingHandCursor)
        refresh_projects_btn.setStyleSheet("""
            QPushButton {
                background-color: #e8f5e9;
                border: 1px solid #c8e6c9;
                border-radius: 6px;
                padding: 3px;
                color: #000000;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #c8e6c9;
            }
        """)
        
        project_header_layout.addWidget(refresh_projects_btn)
        project_layout.addWidget(project_header)

        # Danh sách dự án cải tiến
        self.project_list = QListWidget()
        self.project_list.setIconSize(QSize(32, 32))
        self.project_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 6px;
                background-color: #f8f8f8;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
                border-radius: 4px;
                margin: 2px 0px;
            }
            QListWidget::item:selected {
                background-color: #e8f5e9;
                color: #2e7d32;
            }
            QListWidget::item:hover:!selected {
                background-color: #f0f0f0;
            }
        """)
        self.project_list.itemDoubleClicked.connect(self.open_project)
        self.project_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.project_list.customContextMenuRequested.connect(self.show_project_context_menu)
        project_layout.addWidget(self.project_list)

        left_layout.addWidget(project_group)

        # Right Panel: Project Details - Thiết kế card
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.details_group = QGroupBox("Chi Tiết Dự Án")
        self.details_group.setVisible(False)
        self.details_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 8px;
                margin-top: 8px;  /* Điều chỉnh lên cao hơn */
                background-color: #ffffff;
                padding: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
                color: #2e7d32;
                background-color: #ffffff;  /* Thêm nền trắng cho tiêu đề */
            }
        """)
        
        details_layout = QVBoxLayout(self.details_group)
        details_layout.setSpacing(12)

        # Tiêu đề dự án cải tiến
        project_header = QWidget()
        project_header.setStyleSheet("background-color: #e8f5e9; border-radius: 6px; padding: 5px;")
        project_header_layout = QHBoxLayout(project_header)
        project_header_layout.setContentsMargins(10, 5, 10, 5)
        
        self.project_name_label = QLabel()
        self.project_name_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.project_name_label.setStyleSheet("color: #2e7d32; background-color: transparent;")
        
        rename_btn = QPushButton()
        rename_btn.setText("Đổi tên")
        rename_btn.setFixedSize(80, 32)  # Điều chỉnh kích thước cho phù hợp với text
        rename_btn.setToolTip("Đổi tên dự án")
        rename_btn.clicked.connect(self.rename_project)
        rename_btn.setCursor(Qt.PointingHandCursor)
        rename_btn.setStyleSheet("""
            QPushButton {
                background-color: #c8e6c9;
                color: #000000;
                border-radius: 6px;
                padding: 3px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #a5d6a7;
            }
        """)
        
        project_header_layout.addWidget(self.project_name_label, 1)
        project_header_layout.addWidget(rename_btn)
        details_layout.addWidget(project_header)

        self.project_path_label = QLabel()
        self.project_path_label.setStyleSheet("font-style: italic; color: #666; padding: 0px 5px;")
        details_layout.addWidget(self.project_path_label)

        # Tab thư mục với thiết kế hiện đại
        self.folder_tabs = QTabWidget()
        self.folder_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 6px;
                background-color: #f8f8f8;
                padding: 5px;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                padding: 10px 16px;
                margin-right: 3px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                border: 1px solid #e0e0e0;
                border-bottom: none;
                min-width: 80px;
            }
            QTabBar::tab:selected {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background-color: #e8f5e9;
            }
        """)
        self.folder_tabs.currentChanged.connect(self.on_tab_changed)
        details_layout.addWidget(self.folder_tabs)

        # Nút chức năng với thiết kế hiện đại
        actions_widget = QWidget()
        actions_widget.setStyleSheet("background-color: #f5f5f5; border-radius: 6px; padding: 5px;")
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(5, 5, 5, 5)

        # Auto-refresh toggle và các nút cải tiến
        self.auto_refresh_check = QCheckBox("Tự Động")
        self.auto_refresh_check.setChecked(self.auto_refresh)
        self.auto_refresh_check.toggled.connect(self.toggle_auto_refresh)
        self.auto_refresh_check.setCursor(Qt.PointingHandCursor)
        self.auto_refresh_check.setStyleSheet("""
            QCheckBox {
                padding: 5px;
                color: #333333;  /* Đảm bảo màu chữ đủ tối */
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
                border: 2px solid #4CAF50;
                border-radius: 3px;
            }
        """)
        actions_layout.addWidget(self.auto_refresh_check)
        
        # Nút mở thư mục dự án - với màu nổi bật
        open_folder_btn = QPushButton("Mở Dự Án")
        open_folder_btn.setIcon(QIcon("resources/icons/folder.png"))
        open_folder_btn.setIconSize(QSize(18, 18))
        open_folder_btn.setToolTip("Mở thư mục dự án trong File Explorer")
        open_folder_btn.clicked.connect(self.open_project_folder)
        open_folder_btn.setCursor(Qt.PointingHandCursor)
        open_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1b5e20;
            }
            QPushButton:pressed {
                background-color: #1b5e20;
            }
        """)
        actions_layout.addWidget(open_folder_btn)

        
        # Nút làm mới - đặt ở cùng hàng với các nút khác
        reload_btn = QPushButton("Làm Mới")
        reload_btn.setIcon(QIcon("resources/icons/reload.png"))
        reload_btn.setIconSize(QSize(18, 18))
        reload_btn.setToolTip("Làm mới danh sách file")
        reload_btn.clicked.connect(self.force_reload_files)
        reload_btn.setCursor(Qt.PointingHandCursor)
        reload_btn.setStyleSheet("""
            QPushButton {
                background-color: #e8f5e9;
                border-radius: 6px;
                padding: 8px 16px;
                color: #2e7d32;  /* Màu chữ tối hơn */
                border: 1px solid #c8e6c9;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c8e6c9;
            }
        """)
        actions_layout.addWidget(reload_btn)

        # Nút thêm file
        add_files_btn = QPushButton("Thêm File")
        add_files_btn.setIcon(QIcon("resources/icons/add_file.png"))
        add_files_btn.setIconSize(QSize(18, 18))
        add_files_btn.clicked.connect(self.add_file_to_current_folder)
        add_files_btn.setCursor(Qt.PointingHandCursor)
        add_files_btn.setStyleSheet("""
            QPushButton {
                background-color: #e8f5e9;
                color: #000000;
                border: 1px solid #c8e6c9;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c8e6c9;
            }
        """)
        actions_layout.addWidget(add_files_btn)

        # Nút sắp xếp
        organize_btn = QPushButton("Sắp Xếp")
        organize_btn.setIcon(QIcon("resources/icons/organize.png"))
        organize_btn.setIconSize(QSize(18, 18))
        organize_btn.setToolTip("Di chuyển các file trong thư mục gốc vào thư mục phân loại phù hợp")
        organize_btn.clicked.connect(self.organize_project_folder)
        organize_btn.setCursor(Qt.PointingHandCursor)
        organize_btn.setStyleSheet("""
            QPushButton {
                background-color: #e8f5e9;
                color: #000000;
                border: 1px solid #c8e6c9;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c8e6c9;
            }
        """)
        actions_layout.addWidget(organize_btn)

        # Nút nén dự án
        zip_btn = QPushButton("Nén Dự Án")
        zip_btn.setIcon(QIcon("resources/icons/zip.png"))
        zip_btn.setIconSize(QSize(18, 18))
        zip_btn.clicked.connect(self.archive_project)
        zip_btn.setCursor(Qt.PointingHandCursor)
        zip_btn.setStyleSheet("""
            QPushButton {
                background-color: #e8f5e9;
                color: #000000;
                border: 1px solid #c8e6c9;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c8e6c9;
            }
        """)
        actions_layout.addWidget(zip_btn)

        # Nút xóa dự án
        delete_btn = QPushButton("Xóa Dự Án")
        delete_btn.setIcon(QIcon("resources/icons/delete.png"))
        delete_btn.setIconSize(QSize(18, 18))
        delete_btn.clicked.connect(self.delete_project)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
            }
            QPushButton:hover {
                background-color: #e53935;
            }
        """)
        actions_layout.addWidget(delete_btn)

        details_layout.addWidget(actions_widget)
        right_layout.addWidget(self.details_group)

        # Add panels to splitter
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([300, 700])
        main_layout.addWidget(main_splitter)

        # Footer với nút quay về
        footer_widget = QWidget()
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 5, 0, 0)
        
        # Version label
        version_label = QLabel("v1.0.0")
        version_label.setStyleSheet("color: #888; font-style: italic;")
        footer_layout.addWidget(version_label)
        
        # Spacer
        footer_layout.addStretch(1)
        
        # Back Button
        back_btn = QPushButton("Quay Về Tool Hub")
        back_btn.setIcon(QIcon("resources/icons/back.png"))
        back_btn.setIconSize(QSize(18, 18))
        back_btn.clicked.connect(self.back_to_tool_hub)
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #607d8b;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #546e7a;
            }
        """)
        footer_layout.addWidget(back_btn)

        main_layout.addWidget(footer_widget)

        self.statusBar().showMessage("Sẵn sàng")
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background-color: #f5f5f5;
                color: #555;
                padding: 5px;
                border-top: 1px solid #ddd;
            }
        """)

        # Thêm chức năng kéo thả file cho toàn bộ cửa sổ
        self.setAcceptDrops(True)

        # Setup refresh timer
        self.setup_refresh_timer()

    def setStyleSheet(self, stylesheet):
        """Override stylesheet để kết hợp style mặc định với style tùy chỉnh"""
        super().setStyleSheet(stylesheet + """
            QMainWindow, QWidget {
                background-color: #f5f5f5;
                color: #333;
                font-family: Arial, sans-serif;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
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
            }
            QListWidget::item {
                border-bottom: 1px solid #eee;
                padding: 8px;
            }
            QListWidget::item:selected {
                background-color: #e8f5e9;
                color: #2e7d32;
                border-radius: 4px;
            }
            QLineEdit, QTextEdit {
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 8px;
                selection-background-color: #a5d6a7;
            }
            QMessageBox {
                background-color: #ffffff;
            }
            QMenuBar {
                background-color: #f5f5f5;
                color: #333;
                border-bottom: 1px solid #ddd;
            }
            QMenu {
                background-color: #ffffff;
                border: 1px solid #ddd;
                border-radius: 6px;
            }
            QMenu::item {
                padding: 6px 20px 6px 10px;
                border-radius: 4px;
                margin: 3px;
            }
            QMenu::item:selected {
                background-color: #e8f5e9;
                color: #2e7d32;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #f0f0f0;
                width: 12px;
                margin: 0px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #c0c0c0;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a0a0a0;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

    def setup_refresh_timer(self):
        """Setup timer for periodic refresh"""
        if self.refresh_timer is None:
            self.refresh_timer = QTimer()
            self.refresh_timer.timeout.connect(self.refresh_if_needed)
            
        if self.auto_refresh:
            self.refresh_timer.start(3000)  # Check every 3 seconds (increased frequency)
        else:
            if self.refresh_timer.isActive():
                self.refresh_timer.stop()

    def toggle_auto_refresh(self, enabled):
        """Toggle auto-refresh on/off"""
        self.auto_refresh = enabled
        self.setup_refresh_timer()
        if enabled:
            self.statusBar().showMessage("Đã bật tự động làm mới", 2000)
        else:
            self.statusBar().showMessage("Đã tắt tự động làm mới", 2000)

    def refresh_if_needed(self):
        """Check if refresh is needed and refresh if so"""
        if not self.current_project or not os.path.exists(self.current_project):
            return
            
        has_changes = False
        
        try:
            # Get metadata
            metadata_file = os.path.join(self.current_project, "project.json")
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            # Check if root directory has new files to organize
            if self.auto_organize:
                root_files = [f for f in os.listdir(self.current_project) 
                             if os.path.isfile(os.path.join(self.current_project, f)) 
                             and f != "project.json"]
                if root_files:
                    self.organize_project_folder(silent=True)
                    has_changes = True
            
            # Check if any folder has changes
            for folder_name in metadata["folders"]:
                folder_path = os.path.join(self.current_project, folder_name)
                
                if not os.path.exists(folder_path):
                    continue
                
                # Get current files in the folder
                current_files = set(os.path.basename(f) for f in self.project_manager.get_folder_files(self.current_project, folder_name))
                
                # Get displayed files in the UI
                file_list = self.get_file_list_for_folder(folder_name)
                if not file_list:
                    continue
                    
                displayed_files = set()
                for i in range(file_list.count()):
                    item = file_list.item(i)
                    displayed_files.add(os.path.basename(item.data(Qt.UserRole)))
                
                # If there's a difference, refresh this folder
                if current_files != displayed_files:
                    self.load_folder_files(file_list, folder_name)
                    has_changes = True
                    
                # Check for file size or modification time changes
                for i in range(file_list.count()):
                    item = file_list.item(i)
                    file_path = item.data(Qt.UserRole)
                    if os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        file_mtime = os.path.getmtime(file_path)
                        
                        # Store size and mtime in item data if not already there
                        stored_size = item.data(Qt.UserRole + 1)
                        stored_mtime = item.data(Qt.UserRole + 2)
                        
                        if stored_size is None or stored_mtime is None:
                            item.setData(Qt.UserRole + 1, file_size)
                            item.setData(Qt.UserRole + 2, file_mtime)
                        elif stored_size != file_size or stored_mtime != file_mtime:
                            # File has changed, update the display
                            self.load_folder_files(file_list, folder_name)
                            has_changes = True
                            break
        
        except Exception as e:
            # Silently ignore errors during background refresh
            print(f"Auto-refresh error: {e}")
        
        # Update status bar if changes detected
        if has_changes:
            self.statusBar().showMessage("Đã tự động cập nhật danh sách file", 2000)

    def force_reload_files(self):
        """Force reload files with visual confirmation"""
        if not self.current_project:
            QMessageBox.warning(self, "Thông báo", "Không có dự án nào được mở.")
            return
            
        # Show loading indicator in status bar
        self.statusBar().showMessage("Đang tải lại dự án...")
        
        # Use a single-shot timer to allow UI update
        QTimer.singleShot(100, lambda: self._perform_reload())

    def _perform_reload(self):
        """Actually perform the reload after UI update"""
        try:
            # Reload all folder files
            self.reload_files()
            
            # Also check for files to organize
            self.organize_project_folder(silent=True)
            
            # Không hiển thị thông báo popup nữa, chỉ cập nhật thanh trạng thái
            # Update status
            self.statusBar().showMessage("Đã làm mới hoàn tất", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể làm mới dự án: {str(e)}")
            self.statusBar().showMessage(f"Lỗi: {str(e)}", 3000)

    def load_projects(self):
        """Tải danh sách dự án"""
        self.project_list.clear()
        projects = self.project_manager.get_project_list()
        for project_dir, metadata in projects:
            name = metadata.get("name", os.path.basename(project_dir))
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, project_dir)
            item.setIcon(QIcon("resources/icons/project_manager.png"))
            item.setToolTip(project_dir)
            self.project_list.addItem(item)
        if not projects:
            self.statusBar().showMessage("Không có dự án nào. Hãy tạo dự án mới!")
        else:
            self.statusBar().showMessage(f"Đã tải {len(projects)} dự án")

    def create_project(self):
        """Tạo dự án mới"""
        project_name, ok = QInputDialog.getText(self, "Tạo Dự Án Mới", "Nhập tên dự án:")
        if ok and project_name:
            try:
                project_dir = self.project_manager.create_project(project_name)
                QMessageBox.information(self, "Thành Công", f"Đã tạo dự án '{project_name}' tại:\n{project_dir}")
                self.load_projects()
                self.open_project_from_path(project_dir)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể tạo dự án: {str(e)}")

    def open_project(self, item):
        """Mở dự án được chọn"""
        project_dir = item.data(Qt.UserRole)
        self.open_project_from_path(project_dir)

    def open_project_from_path(self, project_dir):
        """Mở dự án từ đường dẫn"""
        try:
            metadata = self.project_manager.open_project(project_dir)
            self.current_project = project_dir
            self.project_name_label.setText(metadata["name"])
            self.project_path_label.setText(f"Đường dẫn: {project_dir}")
            self.details_group.setVisible(True)
            self.folder_tabs.clear()
            
            # Tự động sắp xếp file khi mở dự án
            self.organize_project_folder(silent=True)
            
            for folder_name, description in metadata["folders"].items():
                tab_widget = QWidget()
                tab_layout = QVBoxLayout(tab_widget)
                desc_label = QLabel(description)
                desc_label.setStyleSheet("color: #666; font-style: italic;")
                tab_layout.addWidget(desc_label)
                file_list = DragDropFileList(folder_name)
                file_list.files_dropped.connect(self.handle_files_dropped)
                file_list.setContextMenuPolicy(Qt.CustomContextMenu)
                file_list.customContextMenuRequested.connect(
                    lambda pos, folder=folder_name: self.show_file_context_menu(pos, folder))
                files = self.project_manager.get_folder_files(project_dir, folder_name)
                for file_path in files:
                    filename = os.path.basename(file_path)
                    item = QListWidgetItem(filename)
                    item.setData(Qt.UserRole, file_path)
                    file_list.addItem(item)
                tab_layout.addWidget(file_list)
                self.folder_tabs.addTab(tab_widget, QIcon("resources/icons/folder.png"), folder_name.capitalize())
            self.current_folder = list(metadata["folders"].keys())[0] if metadata["folders"] else None
            self.statusBar().showMessage(f"Đã mở dự án: {metadata['name']}")
            
            # Cập nhật và lưu trạng thái dự án hiện tại
            self.project_manager.current_project = project_dir
            self.project_manager.save_config()
            
            # Ensure auto-refresh is active when opening a project
            self.setup_refresh_timer()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể mở dự án: {str(e)}")

    def select_project_folder(self):
        """Mở dự án bằng cách chọn thư mục dự án"""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Chọn Thư Mục Dự Án", self.project_manager.base_dir)
        
        if folder_path and os.path.isdir(folder_path):
            try:
                # Kiểm tra xem đây có phải là thư mục dự án hợp lệ không
                if os.path.exists(os.path.join(folder_path, "project.json")):
                    self.open_project_from_path(folder_path)
                else:
                    reply = QMessageBox.question(
                        self,
                        "Thư mục không phải dự án",
                        f"Thư mục '{folder_path}' không chứa file project.json.\n\nBạn có muốn tạo dự án mới từ thư mục này không?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    
                    if reply == QMessageBox.Yes:
                        project_name, ok = QInputDialog.getText(
                            self, "Tạo Dự Án Mới", "Nhập tên dự án:",
                            text=os.path.basename(folder_path)
                        )
                        if ok and project_name:
                            # Tạo dự án mới với tên được nhập và nhập dữ liệu từ thư mục đã chọn
                            try:
                                project_dir = self.project_manager.create_project(project_name)
                                # TODO: Copy files from folder_path to project_dir if needed
                                self.load_projects()
                                self.open_project_from_path(project_dir)
                            except Exception as e:
                                QMessageBox.critical(self, "Lỗi", f"Không thể tạo dự án: {str(e)}")
                
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể mở dự án: {str(e)}")
                
    def handle_files_dropped(self, file_paths, folder_name=None):
        """Xử lý khi file được kéo thả vào thư mục"""
        if not self.current_project:
            QMessageBox.warning(self, "Lỗi", "Không có dự án nào được mở.")
            return
            
        # Nếu có chỉ định folder_name, sử dụng nó
        # Nếu không, để project_manager tự động phát hiện
        for file_path in file_paths:
            try:
                self.project_manager.add_file(self.current_project, folder_name, file_path)
            except Exception as e:
                QMessageBox.warning(self, "Lỗi", 
                    f"Không thể thêm file {os.path.basename(file_path)}: {str(e)}")
                
        # Nếu không chỉ định folder_name, có thể file đã được phân loại vào nhiều thư mục
        # Nên cần tải lại tất cả các thư mục
        if folder_name is None:
            for folder in self.project_manager.DEFAULT_FOLDERS:
                file_list = self.get_file_list_for_folder(folder)
                if file_list:
                    self.load_folder_files(file_list, folder)
        else:
            # Nếu chỉ định folder_name, chỉ cập nhật thư mục đó
            file_list = self.get_file_list_for_folder(folder_name)
            if file_list:
                self.load_folder_files(file_list, folder_name)
        
        # Làm mới danh sách file sau khi thêm
        self.reload_files()

    def handle_auto_sorted_files(self, file_paths):
        """Xử lý các file được thả vào và tự động sắp xếp"""
        if not self.current_project:
            QMessageBox.warning(self, "Lỗi", "Không có dự án nào được mở.")
            return
        
        sorted_files = {}  # dictionary để lưu file đã sắp xếp theo thư mục
        
        for file_path in file_paths:
            try:
                # Tự động phát hiện và thêm file vào thư mục thích hợp
                folder_name = self.project_manager.detect_file_type(file_path)
                new_path = self.project_manager.add_file(self.current_project, folder_name, file_path)
                
                # Lưu lại để cập nhật UI
                if folder_name not in sorted_files:
                    sorted_files[folder_name] = []
                sorted_files[folder_name].append(new_path)
                
            except Exception as e:
                QMessageBox.warning(self, "Lỗi", 
                    f"Không thể thêm file {os.path.basename(file_path)}: {str(e)}")
        
        # Cập nhật UI cho từng thư mục
        for folder_name, files in sorted_files.items():
            file_list = self.get_file_list_for_folder(folder_name)
            if file_list:
                self.load_folder_files(file_list, folder_name)
        
        # Hiển thị thông báo tóm tắt
        if sorted_files:
            total_files = sum(len(files) for files in sorted_files.values())
            summary = "Đã thêm và phân loại tự động:\n"
            for folder, files in sorted_files.items():
                summary += f"- {folder}: {len(files)} file\n"
            
            self.statusBar().showMessage(f"Đã thêm {total_files} file vào dự án")
            QMessageBox.information(self, "Thêm file thành công", summary)
        
        # Sau khi hoàn tất, tự động làm mới các danh sách
        self.reload_files()

    def reload_files(self):
        """Làm mới danh sách file trong tất cả các thư mục"""
        if not self.current_project:
            return
            
        # Lấy metadata dự án
        metadata_file = os.path.join(self.current_project, "project.json")
        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            # Cập nhật từng tab
            for folder_name in metadata["folders"]:
                file_list = self.get_file_list_for_folder(folder_name)
                if file_list:
                    self.load_folder_files(file_list, folder_name)
            
            self.statusBar().showMessage("Đã làm mới danh sách file")
        except Exception as e:
            self.statusBar().showMessage(f"Lỗi khi làm mới: {str(e)}")

    def get_file_list_for_folder(self, folder_name):
        """Lấy widget danh sách file cho một thư mục"""
        for i in range(self.folder_tabs.count()):
            if self.folder_tabs.tabText(i).lower() == folder_name.capitalize().lower():
                tab_widget = self.folder_tabs.widget(i)
                for child in tab_widget.children():
                    if isinstance(child, DragDropFileList) and child.folder_name == folder_name:
                        return child
        return None

    def show_project_context_menu(self, pos):
        """Hiển thị menu ngữ cảnh cho danh sách dự án"""
        global_pos = self.project_list.mapToGlobal(pos)
        selected_item = self.project_list.currentItem()
        
        if selected_item:
            menu = QMenu(self)
            
            open_action = QAction("Mở dự án", self)
            open_action.triggered.connect(lambda: self.open_project(selected_item))
            
            rename_action = QAction("Đổi tên", self)
            rename_action.triggered.connect(self.rename_project)
            
            archive_action = QAction("Nén dự án", self)
            archive_action.triggered.connect(self.archive_project)
            
            delete_action = QAction("Xóa dự án", self)
            delete_action.triggered.connect(self.delete_project)
            
            menu.addAction(open_action)
            menu.addAction(rename_action)
            menu.addAction(archive_action)
            menu.addSeparator()
            menu.addAction(delete_action)
            
            menu.exec_(global_pos)
    
    def show_file_context_menu(self, pos, folder_name):
        """Hiển thị menu ngữ cảnh cho danh sách file"""
        file_list = self.get_file_list_for_folder(folder_name)
        if not file_list:
            return
            
        global_pos = file_list.mapToGlobal(pos)
        selected_item = file_list.currentItem()
        
        if selected_item:
            menu = QMenu(self)
            
            open_action = QAction("Mở file", self)
            open_action.triggered.connect(lambda: self.open_file(selected_item.data(Qt.UserRole)))
            
            rename_action = QAction("Đổi tên", self)
            rename_action.triggered.connect(lambda: self.rename_file(selected_item.data(Qt.UserRole)))
            
            delete_action = QAction("Xóa file", self)
            delete_action.triggered.connect(lambda: self.delete_file(selected_item.data(Qt.UserRole)))
            
            menu.addAction(open_action)
            menu.addAction(rename_action)
            menu.addSeparator()
            menu.addAction(delete_action)
            
            menu.exec_(global_pos)

    def add_file_to_current_folder(self):
        """Thêm file vào thư mục hiện tại"""
        if not self.current_project or not self.current_folder:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một thư mục.")
            return
        
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Chọn File", "")
        if file_paths:
            self.handle_files_dropped(file_paths, self.current_folder)

    def load_folder_files(self, file_list_widget, folder_name):
        """Tải danh sách file trong một thư mục - Cải tiến hiển thị"""
        if not self.current_project:
            return
            
        file_list_widget.clear()
        files = self.project_manager.get_folder_files(self.current_project, folder_name)
        
        for file_path in files:
            filename = os.path.basename(file_path)
            item = QListWidgetItem()
            
            # Thiết lập font cho item
            font = QFont("Arial", 9)
            item.setFont(font)
            
            # Hiển thị tên file với icon và thông tin kích thước
            try:
                file_size = os.path.getsize(file_path)
                if file_size < 1024:
                    size_str = f"{file_size} B"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size/1024:.1f} KB"
                else:
                    size_str = f"{file_size/(1024*1024):.1f} MB"
                    
                # Thay đổi định dạng hiển thị - không sử dụng HTML tags
                item.setText(filename)
                item.setToolTip(f"{file_path}\nKích thước: {size_str}")
                
                # Lưu thông tin kích thước để hiển thị riêng
                item.setData(Qt.UserRole + 3, size_str)
            except:
                item.setText(filename)
            
            item.setData(Qt.UserRole, file_path)
            
            # Store file size and modification time for change detection
            if os.path.exists(file_path):
                try:
                    file_size = os.path.getsize(file_path)
                    file_mtime = os.path.getmtime(file_path)
                    item.setData(Qt.UserRole + 1, file_size)
                    item.setData(Qt.UserRole + 2, file_mtime)
                except:
                    pass
                    
            # Set icon based on file extension
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
                item.setIcon(QIcon("resources/icons/image.png"))
            elif ext in ['.mp4', '.avi', '.mov', '.mkv', '.wmv']:
                item.setIcon(QIcon("resources/icons/video.png"))
            elif ext in ['.mp3', '.wav', '.aac', '.flac']:
                item.setIcon(QIcon("resources/icons/audio.png"))
            elif ext == '.srt':
                item.setIcon(QIcon("resources/icons/subtitle.png"))
            else:
                item.setIcon(QIcon("resources/icons/file.png"))
                    
            file_list_widget.addItem(item)

    def on_tab_changed(self, index):
        """Xử lý khi chuyển tab thư mục"""
        if index >= 0:
            self.current_folder = self.folder_tabs.tabText(index).lower()
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and self.current_project:
            event.accept()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() and self.current_project:
            event.accept()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        if event.mimeData().hasUrls() and self.current_project:
            event.accept()
            file_paths = [url.toLocalFile() for url in event.mimeData().urls() 
                         if os.path.isfile(url.toLocalFile())]
            if file_paths:
                self.handle_auto_sorted_files(file_paths)
        else:
            event.ignore()
    
    def rename_project(self):
        """Đổi tên dự án hiện tại"""
        if not self.current_project:
            return
            
        # Nếu được gọi từ menu ngữ cảnh dự án
        selected_item = self.project_list.currentItem()
        if selected_item:
            project_dir = selected_item.data(Qt.UserRole)
            metadata_file = os.path.join(project_dir, "project.json")
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                current_name = metadata.get("name", "")
            except:
                current_name = os.path.basename(project_dir).split('_')[0]
        else:
            # Nếu được gọi từ nút trong chi tiết dự án
            current_name = self.project_name_label.text()
        
        new_name, ok = QInputDialog.getText(self, "Đổi Tên Dự Án", "Nhập tên mới:", text=current_name)
        
        if ok and new_name:
            try:
                self.project_manager.rename_project(self.current_project, new_name)
                self.project_name_label.setText(new_name)
                self.load_projects()
                self.statusBar().showMessage(f"Đã đổi tên dự án thành '{new_name}'")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể đổi tên dự án: {str(e)}")
    
    def archive_project(self):
        """Nén dự án thành file zip"""
        if not self.current_project:
            project_dir = None
            selected_item = self.project_list.currentItem()
            if selected_item:
                project_dir = selected_item.data(Qt.UserRole)
            
            if not project_dir:
                QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một dự án để nén.")
                return
        else:
            project_dir = self.current_project
        
        try:
            output_path = self.project_manager.archive_project(project_dir)
            QMessageBox.information(self, "Thành Công", f"Đã nén dự án thành công.\nFile được lưu tại:\n{output_path}")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể nén dự án: {str(e)}")
    
    def delete_project(self):
        """Xóa dự án hiện tại"""
        if not self.current_project:
            project_dir = None
            selected_item = self.project_list.currentItem()
            if selected_item:
                project_dir = selected_item.data(Qt.UserRole)
            
            if not project_dir:
                QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một dự án để xóa.")
                return
        else:
            project_dir = self.current_project
        
        reply = QMessageBox.question(
            self, 
            "Xác nhận xóa", 
            f"Bạn có chắc chắn muốn xóa dự án này?\nDự án sẽ bị xóa vĩnh viễn.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                import shutil
                if os.path.exists(project_dir):
                    shutil.rmtree(project_dir)
                
                self.load_projects()
                
                if self.current_project == project_dir:
                    self.current_project = None
                    self.details_group.setVisible(False)
                
                QMessageBox.information(self, "Thành Công", "Đã xóa dự án thành công.")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể xóa dự án: {str(e)}")
    
    def open_file(self, file_path):
        """Mở file với ứng dụng mặc định của hệ thống"""
        try:
            import subprocess
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            elif os.name == 'posix':  # macOS, Linux
                subprocess.Popen(['xdg-open', file_path])
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể mở file: {str(e)}")
    
    def rename_file(self, file_path):
        """Đổi tên file"""
        if not file_path or not os.path.exists(file_path):
            return
            
        current_name = os.path.basename(file_path)
        new_name, ok = QInputDialog.getText(self, "Đổi tên file", "Nhập tên file mới:", text=current_name)
        
        if ok and new_name:
            try:
                new_path = self.project_manager.rename_file(file_path, new_name)
                
                # Tìm và cập nhật item trong list widget
                for i in range(self.folder_tabs.count()):
                    tab_widget = self.folder_tabs.widget(i)
                    for child in tab_widget.children():
                        if isinstance(child, QListWidget):
                            for j in range(child.count()):
                                item = child.item(j)
                                if item and item.data(Qt.UserRole) == file_path:
                                    item.setText(os.path.basename(new_path))
                                    item.setData(Qt.UserRole, new_path)
                                    break
                
                self.statusBar().showMessage(f"Đã đổi tên file thành '{new_name}'")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể đổi tên file: {str(e)}")
    
    def delete_file(self, file_path):
        """Xóa file khỏi dự án"""
        if not file_path or not os.path.exists(file_path):
            return
            
        reply = QMessageBox.question(
            self, 
            "Xác nhận xóa", 
            f"Bạn có chắc chắn muốn xóa file '{os.path.basename(file_path)}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.project_manager.delete_file(file_path)
                
                # Tìm và xóa item trong list widget
                for i in range(self.folder_tabs.count()):
                    tab_widget = self.folder_tabs.widget(i)
                    for child in tab_widget.children():
                        if isinstance(child, QListWidget):
                            for j in range(child.count()):
                                item = child.item(j)
                                if item and item.data(Qt.UserRole) == file_path:
                                    child.takeItem(j)
                                    break
                
                self.statusBar().showMessage(f"Đã xóa file '{os.path.basename(file_path)}'")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể xóa file: {str(e)}")
    
    def back_to_tool_hub(self):
        """Quay về Tool Hub"""
        from ui.main_menu import MainMenu
        self.main_menu = MainMenu()
        self.main_menu.show()
        self.close()

    def change_base_directory(self):
        """Thay đổi thư mục cơ sở lưu dự án"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Chọn thư mục lưu dự án", self.project_manager.base_dir)
        
        if dir_path and os.path.isdir(dir_path):
            try:
                # Cập nhật thư mục cơ sở mới
                self.project_manager.change_base_directory(dir_path)
                self.base_dir_label.setText(dir_path)
                
                # Tải lại danh sách dự án
                self.load_projects()
                
                # Lưu lại trong cấu hình
                self.project_manager.change_base_directory(dir_path)
                self.base_dir_label.setText(dir_path)
                
                # Thông báo thành công
                self.statusBar().showMessage(f"Đã thay đổi thư mục lưu dự án")
                
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể thay đổi thư mục lưu dự án: {str(e)}")

    def organize_project_folder(self, silent=False):
        """Sắp xếp các file trong thư mục gốc vào thư mục phân loại phù hợp"""
        if not self.current_project:
            if not silent:
                QMessageBox.warning(self, "Lỗi", "Không có dự án nào được mở.")
            return
        
        try:
            # Thực hiện sắp xếp
            result = self.project_manager.organize_project_folder(self.current_project)
            
            # Tổng hợp kết quả
            total_files = 0
            organized_files = {}
            for folder, files in result.items():
                if files:  # Chỉ hiển thị thư mục có file được sắp xếp
                    organized_files[folder] = len(files)
                    total_files += len(files)
            
            # Nếu không yêu cầu im lặng và có file được sắp xếp
            if not silent and total_files > 0:
                # Hiển thị thông báo
                summary = "Đã tự động sắp xếp các file vào thư mục phù hợp:\n"
                for folder, count in organized_files.items():
                    summary += f"- {folder}: {count} file\n"
                
                QMessageBox.information(self, "Sắp xếp hoàn tất", summary)
            
            # Cập nhật lại giao diện
            if total_files > 0:
                for folder in result:
                    if result[folder]:  # Chỉ cập nhật thư mục có thay đổi
                        file_list = self.get_file_list_for_folder(folder)
                        if file_list:
                            self.load_folder_files(file_list, folder)
            
            # Cập nhật trạng thái
            if not silent and total_files > 0:
                self.statusBar().showMessage(f"Đã sắp xếp {total_files} file vào các thư mục phù hợp")
            elif not silent:
                self.statusBar().showMessage("Không có file nào cần sắp xếp")
            
            # Cập nhật UI sau khi sắp xếp
            self.reload_files()
                
        except Exception as e:
            if not silent:
                QMessageBox.critical(self, "Lỗi", f"Không thể sắp xếp thư mục: {str(e)}")

    def closeEvent(self, event):
        """Handle window close event"""
        # Stop the timer when closing
        if self.refresh_timer and self.refresh_timer.isActive():
            self.refresh_timer.stop()
        event.accept()

    def open_project_folder(self):
        """Mở thư mục dự án trong File Explorer"""
        if not self.current_project:
            QMessageBox.warning(self, "Lỗi", "Không có dự án nào được mở.")
            return
            
        try:
            import subprocess
            if os.name == 'nt':  # Windows
                os.startfile(self.current_project)
            elif os.name == 'posix':  # macOS, Linux
                subprocess.Popen(['xdg-open', self.current_project])
            self.statusBar().showMessage("Đã mở thư mục dự án")
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể mở thư mục dự án: {str(e)}")