from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QProgressBar, QTextEdit, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QFont

class UpdateDialog(QDialog):
    """Dialog for handling application updates"""
    
    def __init__(self, new_version, current_version, release_notes, parent=None):
        """Initialize update dialog"""
        super().__init__(parent)
        
        self.new_version = new_version
        self.current_version = current_version
        self.release_notes = release_notes
        self.cancelled = False
        
        self.setWindowTitle("Cập nhật ứng dụng")
        self.setMinimumWidth(500)
        
        self.initUI()
    
    def initUI(self):
        """Initialize UI components"""
        layout = QVBoxLayout(self)
        
        # Version information
        version_layout = QHBoxLayout()
        
        current_ver_label = QLabel(f"<b>Phiên bản hiện tại:</b> {self.current_version}")
        new_ver_label = QLabel(f"<b>Phiên bản mới:</b> {self.new_version}")
        new_ver_label.setStyleSheet("color: green; font-weight: bold;")
        
        version_layout.addWidget(current_ver_label)
        version_layout.addStretch()
        version_layout.addWidget(new_ver_label)
        
        layout.addLayout(version_layout)
        
        # Release notes
        notes_label = QLabel("Các thay đổi trong phiên bản mới:")
        notes_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(notes_label)
        
        notes_edit = QTextEdit()
        notes_edit.setPlainText(self.release_notes)
        notes_edit.setReadOnly(True)
        notes_edit.setFixedHeight(150)
        layout.addWidget(notes_edit)
        
        # Progress information
        self.status_label = QLabel("Sẵn sàng cập nhật")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.update_btn = QPushButton("Cập nhật ngay")
        self.update_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        self.update_btn.clicked.connect(self.accept)
        
        self.cancel_btn = QPushButton("Bỏ qua")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.later_btn = QPushButton("Để sau")
        self.later_btn.clicked.connect(self.later)
        
        button_layout.addWidget(self.later_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.update_btn)
        
        layout.addLayout(button_layout)
    
    def later(self):
        """Handle 'Later' button click"""
        # Just close dialog but don't mark as cancelled
        self.done(QDialog.Rejected)
    
    def reject(self):
        """Handle cancellation"""
        self.cancelled = True
        super().reject()
    
    @pyqtSlot(int, str)
    def update_progress(self, percent, message):
        """Update progress display"""
        if not self.progress_bar.isVisible():
            self.progress_bar.setVisible(True)
            self.update_btn.setEnabled(False)
            self.cancel_btn.setEnabled(False)
            self.later_btn.setEnabled(False)
        
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)
    
    @pyqtSlot(bool, str)
    def update_finished(self, success, message):
        """Handle update completion"""
        if success:
            QMessageBox.information(self, "Cập nhật thành công", 
                                   "Cập nhật đã hoàn tất. Ứng dụng sẽ khởi động lại.")
        else:
            QMessageBox.warning(self, "Lỗi cập nhật", 
                               f"Không thể cập nhật: {message}")
            self.update_btn.setEnabled(True)
            self.cancel_btn.setEnabled(True)
            self.later_btn.setEnabled(True)
