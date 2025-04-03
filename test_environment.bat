@echo off
echo === Tạo môi trường kiểm tra cho KHyTool ===
echo.

REM Use Drive D for testing
set ENV_DIR=D:\KHyTool_TestEnv

REM Tạo môi trường ảo Python
echo Đang tạo môi trường ảo Python trên ổ D...
python -m venv %ENV_DIR%
if %ERRORLEVEL% NEQ 0 (
    echo Lỗi khi tạo môi trường ảo.
    echo Hãy chắc chắn bạn đã cài đặt Python với module venv.
    pause
    exit /b %ERRORLEVEL%
)

REM Kích hoạt môi trường ảo
echo Đang kích hoạt môi trường ảo...
call %ENV_DIR%\Scripts\activate.bat
if %ERRORLEVEL% NEQ 0 (
    echo Lỗi khi kích hoạt môi trường ảo.
    pause
    exit /b %ERRORLEVEL%
)

REM Hiển thị thông tin Python của môi trường
echo Môi trường Python đã được kích hoạt:
python --version
where python
echo.

REM Cài đặt dependencies
echo Đang cài đặt các dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo Cảnh báo: Một số dependencies có thể chưa được cài đặt thành công.
    echo Tiếp tục quá trình...
)

REM Mở terminal mới để người dùng thử nghiệm
echo.
echo === Môi trường kiểm tra đã sẵn sàng ===
echo Bạn có thể chạy "python main.py" để khởi động ứng dụng
echo Hoặc chạy "python enhanced_package.py" để đóng gói ứng dụng
echo.
echo Khi hoàn tất, gõ "deactivate" để thoát môi trường ảo
echo.

REM Giữ terminal mở để người dùng làm việc
cmd /k

@echo off
echo === Chuẩn bị môi trường kiểm thử KHyTool ===

REM Kiểm tra có VirtualBox
where VBoxManage >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo VirtualBox không được tìm thấy. Thay vào đó sẽ tạo thư mục môi trường kiểm thử.
    goto CreateTestFolder
)

echo VirtualBox được tìm thấy. Bạn có thể tạo máy ảo để kiểm tra.
echo.
echo Các bước thực hiện:
echo 1. Tạo máy ảo Windows mới trong VirtualBox
echo 2. Cài đặt Windows (có thể dùng bản Windows 10 Evaluation từ Microsoft)
echo 3. Copy installer KHyTool_Setup.exe vào máy ảo
echo 4. Cài đặt và kiểm tra ứng dụng trong môi trường sạch
echo.
choice /C YN /M "Bạn muốn mở VirtualBox bây giờ?"
if %ERRORLEVEL% EQU 1 (
    start "" "VirtualBox"
)

:CreateTestFolder
echo.
echo Tạo thư mục kiểm thử...
mkdir D:\TestEnvironment 2>nul
copy KHyTool_Setup.exe D:\TestEnvironment\ >nul 2>&1
copy dist\KHyTool\*.* D:\TestEnvironment\ >nul 2>&1
copy bin\ffmpeg.exe D:\TestEnvironment\ >nul 2>&1

echo.
echo Đã tạo thư mục D:\TestEnvironment với các tệp cần thiết.
echo Bạn có thể sao chép thư mục này sang máy tính khác để kiểm tra.
echo.
echo Đường dẫn: D:\TestEnvironment
echo.

choice /C YN /M "Bạn muốn mở thư mục D:\TestEnvironment?"
if %ERRORLEVEL% EQU 1 (
    start "" "D:\TestEnvironment"
)

pause
