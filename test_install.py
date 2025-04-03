#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import importlib
import platform
import time
import shutil
import zipfile
import datetime

class TestInstallation:
    """Kiểm tra cài đặt của KHyTool trong môi trường hiện tại"""
    
    def __init__(self):
        self.all_passed = True
        self.results = []
    
    def run_tests(self):
        """Chạy tất cả các bài kiểm tra"""
        print("=== KIỂM TRA CÀI ĐẶT KHYTOOL ===")
        print(f"Python: {platform.python_version()}")
        print(f"Hệ điều hành: {platform.platform()}")
        print("-" * 50)
        
        # Kiểm tra các thư viện cơ bản
        self.test_basic_dependencies()
        
        # Kiểm tra FFmpeg
        self.test_ffmpeg()
        
        # Kiểm tra yt-dlp
        self.test_ytdlp()
        
        # Kiểm tra khả năng load UI
        self.test_ui_loading()
        
        # Hiển thị kết quả tổng quát
        print("\n" + "=" * 50)
        print("KẾT QUẢ KIỂM TRA:")
        for test, passed, message in self.results:
            status = "✅ ĐẠT" if passed else "❌ LỖI"
            print(f"{status} - {test}: {message}")
        
        print("\nKẾT LUẬN:")
        if self.all_passed:
            print("✅ Tất cả các kiểm tra đều thành công! KHyTool nên hoạt động bình thường.")
        else:
            print("❌ Một số kiểm tra không thành công. KHyTool có thể gặp vấn đề khi chạy.")
    
    def add_result(self, test_name, passed, message):
        """Thêm kết quả kiểm tra"""
        self.results.append((test_name, passed, message))
        if not passed:
            self.all_passed = False
    
    def test_basic_dependencies(self):
        """Kiểm tra các thư viện cơ bản"""
        print("\nĐang kiểm tra các thư viện cơ bản...")
        
        required_modules = [
            ("PyQt5", "Giao diện người dùng"),
            ("numpy", "Xử lý dữ liệu"),
            ("PIL", "Xử lý ảnh"),
            ("cv2", "Xử lý ảnh và video"),
            ("yt_dlp", "Tải video")
        ]
        
        for module, description in required_modules:
            try:
                importlib.import_module(module)
                print(f"  ✓ {module}: Đã cài đặt")
                self.add_result(f"Thư viện {module}", True, "Đã cài đặt")
            except ImportError as e:
                print(f"  ✗ {module}: Không tìm thấy - {str(e)}")
                self.add_result(f"Thư viện {module}", False, f"Không tìm thấy: {str(e)}")
    
    def test_ffmpeg(self):
        """Kiểm tra FFmpeg"""
        print("\nĐang kiểm tra FFmpeg...")
        
        # Kiểm tra thư mục bin của ứng dụng
        bin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")
        ffmpeg_exe = "ffmpeg.exe" if os.name == 'nt' else "ffmpeg"
        ffmpeg_path = os.path.join(bin_dir, ffmpeg_exe)
        
        if os.path.exists(ffmpeg_path):
            print(f"  ✓ FFmpeg: Tìm thấy trong thư mục bin ({ffmpeg_path})")
            self.add_result("FFmpeg (bin)", True, f"Tìm thấy tại {ffmpeg_path}")
            return
        
        # Kiểm tra FFmpeg trong PATH
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                version_line = result.stdout.strip().split("\n")[0]
                print(f"  ✓ FFmpeg: {version_line}")
                self.add_result("FFmpeg (PATH)", True, version_line)
            else:
                print("  ✗ FFmpeg: Lỗi khi chạy")
                self.add_result("FFmpeg", False, "Không thể chạy FFmpeg")
        except (subprocess.SubprocessError, FileNotFoundError):
            print("  ✗ FFmpeg: Không tìm thấy")
            self.add_result("FFmpeg", False, "Không tìm thấy hoặc không thể chạy")
    
    def test_ytdlp(self):
        """Kiểm tra yt-dlp"""
        print("\nĐang kiểm tra yt-dlp...")
        
        try:
            import yt_dlp
            
            # Kiểm tra phương thức get_exe_dir (vấn đề đã phát hiện trước đó)
            has_get_exe_dir = hasattr(yt_dlp.utils, 'get_exe_dir')
            if has_get_exe_dir:
                print("  ✓ yt_dlp.utils.get_exe_dir: Có sẵn")
                self.add_result("yt-dlp get_exe_dir", True, "Phương thức có sẵn")
            else:
                print("  ✗ yt_dlp.utils.get_exe_dir: Không tìm thấy")
                self.add_result("yt-dlp get_exe_dir", False, "Phương thức không có sẵn")
            
            # Kiểm tra phiên bản
            version = yt_dlp.version.__version__
            print(f"  ✓ yt-dlp phiên bản: {version}")
            self.add_result("yt-dlp version", True, f"v{version}")
            
        except ImportError as e:
            print(f"  ✗ yt-dlp: Không thể nhập - {str(e)}")
            self.add_result("yt-dlp", False, f"Không thể nhập: {str(e)}")
    
    def test_ui_loading(self):
        """Kiểm tra khả năng tải giao diện người dùng"""
        print("\nĐang kiểm tra khả năng tải giao diện...")
        
        try:
            from PyQt5.QtWidgets import QApplication
            app = QApplication([])
            
            # Kiểm tra mainmenu
            try:
                from ui.main_menu import MainMenu
                print("  ✓ Có thể nhập MainMenu")
                self.add_result("UI MainMenu", True, "Có thể nhập")
                
                try:
                    window = MainMenu()
                    print("  ✓ Có thể khởi tạo MainMenu")
                    self.add_result("UI MainMenu init", True, "Có thể khởi tạo")
                except Exception as e:
                    print(f"  ✗ Lỗi khi khởi tạo MainMenu: {str(e)}")
                    self.add_result("UI MainMenu init", False, f"Lỗi: {str(e)}")
                    
            except ImportError as e:
                print(f"  ✗ Không thể nhập MainMenu: {str(e)}")
                self.add_result("UI MainMenu", False, f"Không thể nhập: {str(e)}")
        
        except ImportError as e:
            print(f"  ✗ Không thể nhập PyQt5: {str(e)}")
            self.add_result("PyQt5", False, f"Không thể nhập: {str(e)}")

def create_test_package():
    """Create a test package for clean environment installation"""
    print("=== Creating KHyTool Test Package ===")
    
    # Create test directory on drive D
    test_dir = "D:\\KHyTool_TestPackage"
    os.makedirs(test_dir, exist_ok=True)
    
    # Check if installer or standalone app exists
    installer_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "KHyTool_Setup.exe")
    standalone_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", "KHyTool")
    
    if not os.path.exists(installer_path) and not os.path.exists(standalone_path):
        print("Error: Neither installer nor standalone app found.")
        print("Please run build.bat first to create the application package.")
        return False
    
    # Copy installer if available
    if os.path.exists(installer_path):
        print(f"Copying installer: {installer_path}")
        shutil.copy(installer_path, test_dir)
    
    # Copy standalone version
    if os.path.exists(standalone_path):
        print(f"Copying standalone application: {standalone_path}")
        standalone_dest = os.path.join(test_dir, "StandaloneApp")
        os.makedirs(standalone_dest, exist_ok=True)
        
        # Copy all files from standalone app
        for item in os.listdir(standalone_path):
            source_item = os.path.join(standalone_path, item)
            dest_item = os.path.join(standalone_dest, item)
            if os.path.isdir(source_item):
                shutil.copytree(source_item, dest_item, dirs_exist_ok=True)
            else:
                shutil.copy2(source_item, dest_item)
    
    # Create test script
    with open(os.path.join(test_dir, "test_app.bat"), "w") as test_script:
        test_script.write("""@echo off
echo === KHyTool Test Script ===
echo.

echo Checking system information...
systeminfo | findstr /B /C:"OS Name" /C:"OS Version"
echo.

echo Testing standalone version...
if exist StandaloneApp\\KHyTool.exe (
    echo Found standalone executable
    echo Testing FFmpeg...
    if exist StandaloneApp\\bin\\ffmpeg.exe (
        echo FFmpeg found in standalone app
    ) else (
        echo WARNING: FFmpeg not found in standalone app bin directory
    )
    
    choice /C YN /M "Do you want to run the standalone version"
    if %ERRORLEVEL% EQU 1 (
        start "" "StandaloneApp\\KHyTool.exe"
        timeout /t 5
    )
) else (
    echo Standalone version not found
)

echo.
echo Testing installer version...
if exist KHyTool_Setup.exe (
    echo Found installer
    choice /C YN /M "Do you want to run the installer"
    if %ERRORLEVEL% EQU 1 (
        start "" "KHyTool_Setup.exe"
    )
) else (
    echo Installer not found
)

echo.
echo Test complete.
pause
""")
    
    # Create readme
    with open(os.path.join(test_dir, "README.txt"), "w") as readme:
        readme.write(f"""KHyTool Test Package
=================
Created: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

This package contains:
1. Standalone version of KHyTool (in StandaloneApp folder)
2. KHyTool Installer (KHyTool_Setup.exe)
3. Test script (test_app.bat)

Instructions:
1. Copy this entire folder to a clean test system (no Python or FFmpeg installed)
2. Run test_app.bat to test the application
3. Both standalone version and installer should work without requiring Python

Notes:
- The standalone version should have FFmpeg bundled in the bin directory
- The installer will install the app system-wide with necessary components
""")
    
    # Create zip archive on drive D
    zip_path = "D:\\KHyTool_TestPackage.zip"
    print(f"Creating zip archive: {zip_path}")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(test_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, test_dir))
    
    print("\nTest package created successfully!")
    print(f"Directory: {test_dir}")
    print(f"Zip archive: {zip_path}")
    print("\nYou can copy this package to a clean system (without Python or FFmpeg)")
    print("to verify that the application works correctly.")
    
    return True

if __name__ == "__main__":
    tester = TestInstallation()
    tester.run_tests()
    
    print("\nNhấn Enter để thoát...")
    input()
    
    create_test_package()
