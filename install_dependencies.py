import os
import sys
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk
import threading
import traceback

class DependencyInstaller:
    """Utility for installing dependencies required by KHyTool"""
    
    def __init__(self, root):
        self.root = root
        root.title("KHyTool - Cài đặt thành phần phụ thuộc")
        root.geometry("600x450")
        root.resizable(True, True)
        
        # Center window
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f'{width}x{height}+{x}+{y}')
        
        # Main frame with padding
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="Cài đặt thành phần phụ thuộc", 
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=10)
        
        # Description
        desc_text = (
            "Công cụ này sẽ cài đặt các thư viện và thành phần cần thiết "
            "để KHyTool hoạt động đầy đủ chức năng.\n\n"
            "Hãy chọn các thành phần bạn muốn cài đặt:"
        )
        desc_label = ttk.Label(
            main_frame,
            text=desc_text,
            wraplength=550,
            justify="left"
        )
        desc_label.pack(fill="x", pady=10, anchor="w")
        
        # Checkbutton frame
        check_frame = ttk.LabelFrame(main_frame, text="Thành phần cài đặt")
        check_frame.pack(fill="x", pady=10, padx=5)
        
        # Dependencies to install
        self.deps = {
            "basic": tk.BooleanVar(value=True),  # Core requirements
            "ffmpeg": tk.BooleanVar(value=True),  # FFmpeg
            "whisper": tk.BooleanVar(value=True),  # Whisper for subtitles
            "demucs": tk.BooleanVar(value=True),  # Demucs for audio separation
        }
        
        # Descriptions
        descriptions = {
            "basic": "Thư viện cơ bản (PyQt5, cv2, pytesseract, pillow, etc.)",
            "ffmpeg": "FFmpeg - Xử lý video và audio",
            "whisper": "OpenAI Whisper - Tạo phụ đề tự động",
            "demucs": "Demucs - Tách nhạc và giọng hát",
        }
        
        # Create checkboxes
        for i, (key, name) in enumerate(descriptions.items()):
            cb = ttk.Checkbutton(
                check_frame,
                text=name,
                variable=self.deps[key],
                onvalue=True,
                offvalue=False
            )
            cb.grid(row=i, column=0, sticky="w", padx=20, pady=5)
            
            # Add requirements size information
            size_text = ""
            if key == "basic":
                size_text = "~50MB"
            elif key == "ffmpeg":
                size_text = "~70MB"
            elif key == "whisper":
                size_text = "~150MB + models"
            elif key == "demucs":
                size_text = "~1GB với models"
            
            if size_text:
                size_label = ttk.Label(check_frame, text=size_text)
                size_label.grid(row=i, column=1, padx=10)
        
        # Progress frame
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill="x", pady=10, padx=5)
        
        self.progress = ttk.Progressbar(
            progress_frame, 
            orient="horizontal", 
            length=580, 
            mode="determinate"
        )
        self.progress.pack(fill="x", pady=5)
        
        self.status_label = ttk.Label(
            progress_frame,
            text="Chưa bắt đầu",
            font=("Arial", 10),
        )
        self.status_label.pack(fill="x", pady=5)
        
        # Log frame
        log_frame = ttk.LabelFrame(main_frame, text="Log")
        log_frame.pack(fill="both", expand=True, pady=10, padx=5)
        
        self.log_text = tk.Text(log_frame, height=6, width=70, wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Scrollbar for log
        scrollbar = ttk.Scrollbar(self.log_text, orient="vertical", command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=10)
        
        # Install button
        self.install_btn = ttk.Button(
            button_frame,
            text="Cài đặt",
            command=self.start_installation,
            width=15
        )
        self.install_btn.pack(side="left", padx=5)
        
        # Close button
        self.close_btn = ttk.Button(
            button_frame,
            text="Đóng",
            command=root.destroy,
            width=15
        )
        self.close_btn.pack(side="right", padx=5)
        
        # Initialize status
        self.installing = False
    
    def log(self, message):
        """Add message to log"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)  # Scroll to the end
        
    def update_status(self, message, progress=None):
        """Update status label and progress bar"""
        self.status_label.config(text=message)
        if progress is not None and 0 <= progress <= 100:
            self.progress["value"] = progress
        self.root.update_idletasks()  # Force UI update
        
    def start_installation(self):
        """Start the installation process in a separate thread"""
        if self.installing:
            messagebox.showwarning("Đang cài đặt", "Quá trình cài đặt đang diễn ra. Vui lòng đợi.")
            return
        
        # Check if any components are selected
        if not any(var.get() for var in self.deps.values()):
            messagebox.showwarning("Lỗi", "Vui lòng chọn ít nhất một thành phần để cài đặt.")
            return
        
        # Confirm installation
        confirm = messagebox.askokcancel(
            "Xác nhận",
            "Bắt đầu cài đặt các thành phần đã chọn?\n"
            "Quá trình này có thể mất vài phút tùy thuộc vào tốc độ mạng."
        )
        if not confirm:
            return
        
        # Disable UI during installation
        self.install_btn.config(state="disabled")
        self.installing = True
        
        # Clear log
        self.log_text.delete(1.0, tk.END)
        
        # Start installation thread
        thread = threading.Thread(target=self.perform_installation)
        thread.daemon = True
        thread.start()
    
    def perform_installation(self):
        """Perform the actual installation"""
        try:
            # Check Python and pip
            self.update_status("Đang kiểm tra Python và pip...", 5)
            self.log("Kiểm tra Python và pip...")
            
            try:
                pip_version = subprocess.check_output(
                    [sys.executable, "-m", "pip", "--version"], 
                    stderr=subprocess.STDOUT, 
                    text=True
                )
                self.log(f"Phiên bản pip: {pip_version.strip()}")
            except subprocess.CalledProcessError:
                self.log("Không tìm thấy pip! Hãy cài đặt Python và pip trước.")
                self.update_status("Lỗi: Không tìm thấy pip", 0)
                messagebox.showerror("Lỗi", "Không tìm thấy pip. Hãy cài đặt Python và pip trước.")
                self.installing = False
                self.install_btn.config(state="normal")
                return
            
            # Basic dependencies
            if self.deps["basic"].get():
                self.update_status("Đang cài đặt thư viện cơ bản...", 10)
                self.log("\n--- Cài đặt thư viện cơ bản ---")
                
                basic_packages = [
                    "PyQt5", "Pillow", "numpy", "opencv-python", "pytesseract", 
                    "requests", "moviepy", "yt-dlp", "ffmpeg-python"
                ]
                
                for i, package in enumerate(basic_packages):
                    progress = 10 + int(i * 20 / len(basic_packages))
                    self.update_status(f"Đang cài đặt {package}...", progress)
                    
                    try:
                        self.log(f"Đang cài đặt {package}...")
                        subprocess.check_call(
                            [sys.executable, "-m", "pip", "install", "--upgrade", package],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                        self.log(f"✓ Đã cài đặt {package}")
                    except subprocess.CalledProcessError as e:
                        self.log(f"✗ Lỗi khi cài đặt {package}: {str(e)}")
            
            # FFmpeg
            if self.deps["ffmpeg"].get():
                self.update_status("Đang cài đặt FFmpeg...", 30)
                self.log("\n--- Cài đặt FFmpeg ---")
                
                # Use the FFmpegManager to download and install FFmpeg
                self.log("Đang nhập FFmpegManager...")
                
                try:
                    # Add parent directory to sys.path to import from project
                    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    if parent_dir not in sys.path:
                        sys.path.append(parent_dir)
                    
                    # Try to import FFmpegManager
                    from utils.ffmpeg_manager import FFmpegManager
                    
                    self.log("Đang tải và cài đặt FFmpeg...")
                    ffmpeg_manager = FFmpegManager()
                    result = ffmpeg_manager.download_ffmpeg()
                    
                    if result:
                        self.log("✓ Đã cài đặt FFmpeg thành công")
                        ffmpeg_path = ffmpeg_manager.get_ffmpeg_path()
                        if ffmpeg_path:
                            self.log(f"FFmpeg path: {ffmpeg_path}")
                    else:
                        self.log("✗ Không thể cài đặt FFmpeg tự động")
                        
                except ImportError:
                    self.log("Không thể nhập FFmpegManager, thử phương pháp thay thế...")
                    try:
                        # Alternative approach: Install ffmpeg-python which might bring ffmpeg
                        subprocess.check_call(
                            [sys.executable, "-m", "pip", "install", "--upgrade", "ffmpeg-python"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                        self.log("✓ Đã cài đặt ffmpeg-python")
                    except subprocess.CalledProcessError as e:
                        self.log(f"✗ Lỗi khi cài đặt ffmpeg-python: {str(e)}")
                
                except Exception as e:
                    self.log(f"✗ Lỗi khi cài đặt FFmpeg: {str(e)}")
            
            # OpenAI Whisper
            if self.deps["whisper"].get():
                self.update_status("Đang cài đặt OpenAI Whisper...", 50)
                self.log("\n--- Cài đặt OpenAI Whisper ---")
                
                whisper_packages = [
                    "torch", "torchaudio", "openai-whisper"
                ]
                
                for i, package in enumerate(whisper_packages):
                    progress = 50 + int(i * 15 / len(whisper_packages))
                    self.update_status(f"Đang cài đặt {package}...", progress)
                    
                    try:
                        if package == "torch" or package == "torchaudio":
                            # Special case for torch to install the CPU-only version
                            self.log(f"Đang cài đặt {package} (phiên bản CPU)...")
                            subprocess.check_call(
                                [sys.executable, "-m", "pip", "install", "--upgrade", 
                                 f"{package}==2.0.0+cpu", "-f", 
                                 "https://download.pytorch.org/whl/torch_stable.html"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE
                            )
                        else:
                            self.log(f"Đang cài đặt {package}...")
                            subprocess.check_call(
                                [sys.executable, "-m", "pip", "install", "--upgrade", package],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE
                            )
                        self.log(f"✓ Đã cài đặt {package}")
                    except subprocess.CalledProcessError as e:
                        self.log(f"✗ Lỗi khi cài đặt {package}: {str(e)}")
            
            # Demucs (audio separation)
            if self.deps["demucs"].get():
                self.update_status("Đang cài đặt Demucs...", 70)
                self.log("\n--- Cài đặt Demucs ---")
                
                # First check if PyTorch is installed
                try:
                    import torch
                    self.log("PyTorch đã được cài đặt.")
                except ImportError:
                    self.log("PyTorch chưa được cài đặt. Đang cài đặt...")
                    try:
                        subprocess.check_call(
                            [sys.executable, "-m", "pip", "install", "--upgrade", 
                             "torch==2.0.0+cpu", "-f", 
                             "https://download.pytorch.org/whl/torch_stable.html"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                        self.log("✓ Đã cài đặt PyTorch")
                    except subprocess.CalledProcessError as e:
                        self.log(f"✗ Lỗi khi cài đặt PyTorch: {str(e)}")
                
                # Install demucs
                self.update_status("Đang cài đặt demucs...", 80)
                try:
                    self.log("Đang cài đặt demucs...")
                    subprocess.check_call(
                        [sys.executable, "-m", "pip", "install", "--upgrade", "demucs"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    self.log("✓ Đã cài đặt demucs")
                    
                    # Verify installation
                    self.update_status("Đang kiểm tra cài đặt demucs...", 90)
                    subprocess.check_output(
                        [sys.executable, "-m", "demucs", "--version"],
                        stderr=subprocess.STDOUT,
                        text=True
                    )
                    self.log("✓ Demucs đã sẵn sàng sử dụng")
                    
                except subprocess.CalledProcessError as e:
                    self.log(f"✗ Lỗi khi cài đặt hoặc kiểm tra demucs: {str(e)}")
            
            # Installation complete
            self.update_status("Cài đặt hoàn tất!", 100)
            self.log("\n--- CÀI ĐẶT HOÀN TẤT ---")
            
            # Run pip list to show installed packages
            try:
                self.log("\nDanh sách các thư viện đã cài đặt:")
                pip_list = subprocess.check_output(
                    [sys.executable, "-m", "pip", "list"],
                    stderr=subprocess.STDOUT,
                    text=True
                )
                self.log(pip_list)
            except:
                pass
                
            messagebox.showinfo("Hoàn tất", "Đã cài đặt các thành phần đã chọn thành công!")
            
        except Exception as e:
            self.log(f"Lỗi: {str(e)}")
            traceback.print_exc(file=sys.stdout)
            messagebox.showerror("Lỗi", f"Đã xảy ra lỗi: {str(e)}")
        
        finally:
            self.installing = False
            self.install_btn.config(state="normal")

def main():
    """Main function to run the installer as a standalone application"""
    root = tk.Tk()
    app = DependencyInstaller(root)
    root.mainloop()

if __name__ == "__main__":
    main()
