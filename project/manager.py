import os
import shutil
import json
import zipfile
from datetime import datetime
import re

class ProjectManager:
    """Lớp quản lý dự án video"""
    
    # Cập nhật danh sách thư mục, bỏ exports và templates
    DEFAULT_FOLDERS = {
        "images": "Lưu trữ ảnh và thumbnail",
        "videos": "Lưu trữ video nguồn và đầu ra",
        "audio": "Lưu trữ file âm thanh", 
        "subtitles": "Lưu trữ file phụ đề",
    }
    
    # Định nghĩa các nhóm định dạng file
    IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp']
    VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']
    AUDIO_EXTENSIONS = ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a', '.wma']
    SUBTITLE_EXTENSIONS = ['.srt', '.vtt', '.ass', '.ssa', '.sub']
    
    def __init__(self, base_dir=None):
        """
        Khởi tạo project manager
        
        Args:
            base_dir: Đường dẫn thư mục cơ sở để lưu các dự án 
                      (mặc định là "Projects" trong thư mục home của user)
        """
        # Đọc cấu hình từ file
        self.config_file = os.path.join(os.path.expanduser("~"), ".khytool_config.json")
        
        # Đọc cấu hình nếu có
        config = self.load_config()
        
        # Nếu không chỉ định base_dir và có base_dir trong cấu hình, sử dụng cấu hình
        if base_dir is None and "base_dir" in config:
            base_dir = config["base_dir"]
            
        # Nếu vẫn không có base_dir, sử dụng mặc định
        if base_dir is None:
            # Mặc định là thư mục trong home của user
            base_dir = os.path.join(os.path.expanduser("~"), "KHyTool Projects")
            
        self.base_dir = base_dir
        self.current_project = config.get("last_project")
        
        # Đảm bảo thư mục gốc tồn tại
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
        
        # Lưu cấu hình
        self.save_config()
    
    def load_config(self):
        """Tải cấu hình từ file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def save_config(self):
        """Lưu cấu hình xuống file"""
        config = {
            "base_dir": self.base_dir,
            "last_project": self.current_project
        }
        
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except:
            pass  # Không gây lỗi nếu không lưu được cấu hình
    
    def change_base_directory(self, new_base_dir):
        """
        Thay đổi thư mục cơ sở để lưu các dự án
        
        Args:
            new_base_dir: Đường dẫn thư mục cơ sở mới
            
        Returns:
            Đường dẫn thư mục cơ sở mới
        """
        if not os.path.exists(new_base_dir):
            os.makedirs(new_base_dir)
            
        self.base_dir = new_base_dir
        self.save_config()  # Lưu lại cấu hình
        return self.base_dir
    
    def create_project(self, project_name):
        """
        Tạo một dự án mới với cấu trúc thư mục chuẩn
        
        Args:
            project_name: Tên dự án
            
        Returns:
            Đường dẫn tới thư mục dự án vừa tạo
        """
        # Xử lý tên dự án để tránh các ký tự không hợp lệ trong tên thư mục
        safe_name = self._sanitize_filename(project_name)
        if not safe_name:
            raise ValueError("Tên dự án không hợp lệ")
        
        # Tạo thư mục dự án
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_dir = os.path.join(self.base_dir, f"{safe_name}_{timestamp}")
        
        if os.path.exists(project_dir):
            raise FileExistsError(f"Dự án '{project_name}' đã tồn tại")
        
        os.makedirs(project_dir)
        
        # Tạo các thư mục con
        for folder, description in self.DEFAULT_FOLDERS.items():
            os.makedirs(os.path.join(project_dir, folder))
        
        # Tạo file metadata
        metadata = {
            "name": project_name,
            "created": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat(),
            "folders": self.DEFAULT_FOLDERS
        }
        
        with open(os.path.join(project_dir, "project.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)
        
        self.current_project = project_dir
        self.save_config()  # Lưu lại cấu hình
        return project_dir
    
    def open_project(self, project_dir):
        """
        Mở một dự án hiện có
        
        Args:
            project_dir: Đường dẫn thư mục dự án
            
        Returns:
            Thông tin metadata của dự án
        """
        if not os.path.exists(project_dir) or not os.path.isdir(project_dir):
            raise FileNotFoundError(f"Không tìm thấy dự án tại '{project_dir}'")
        
        metadata_file = os.path.join(project_dir, "project.json")
        if not os.path.exists(metadata_file):
            raise ValueError(f"Thư mục '{project_dir}' không chứa dự án hợp lệ")
        
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        
        # Cập nhật thời gian truy cập gần nhất
        metadata["last_accessed"] = datetime.now().isoformat()
        
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)
        
        # Cập nhật dự án hiện tại và lưu cấu hình
        self.current_project = project_dir
        self.save_config()
        
        return metadata
    
    def get_project_list(self):
        """
        Lấy danh sách các dự án hiện có
        
        Returns:
            Danh sách các dự án dưới dạng tuple (project_dir, metadata)
        """
        projects = []
        
        if not os.path.exists(self.base_dir):
            return projects
            
        for item in os.listdir(self.base_dir):
            item_path = os.path.join(self.base_dir, item)
            
            if os.path.isdir(item_path):
                metadata_file = os.path.join(item_path, "project.json")
                
                if os.path.exists(metadata_file):
                    try:
                        with open(metadata_file, "r", encoding="utf-8") as f:
                            metadata = json.load(f)
                            projects.append((item_path, metadata))
                    except:
                        # Nếu không đọc được metadata, thêm dự án với metadata trống
                        projects.append((item_path, {"name": item}))
        
        # Sắp xếp theo thời gian truy cập gần nhất (nếu có)
        projects.sort(key=lambda x: x[1].get("last_accessed", ""), reverse=True)
        
        return projects
    
    def archive_project(self, project_dir, output_path=None, delete_after=False):
        """
        Nén dự án thành file zip để lưu trữ
        
        Args:
            project_dir: Đường dẫn thư mục dự án
            output_path: Đường dẫn file zip đầu ra (mặc định là thư mục cha của dự án)
            delete_after: Có xóa thư mục dự án sau khi nén hay không
            
        Returns:
            Đường dẫn đến file zip vừa tạo
        """
        if not os.path.exists(project_dir) or not os.path.isdir(project_dir):
            raise FileNotFoundError(f"Không tìm thấy dự án tại '{project_dir}'")
        
        # Nếu không chỉ định đường dẫn đầu ra, sử dụng thư mục cha với tên thư mục dự án
        if output_path is None:
            project_name = os.path.basename(project_dir)
            parent_dir = os.path.dirname(project_dir)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(parent_dir, f"{project_name}_{timestamp}.zip")
        
        # Tạo file zip
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(project_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Tính đường dẫn tương đối để giữ cấu trúc thư mục
                    relative_path = os.path.relpath(file_path, start=os.path.dirname(project_dir))
                    zipf.write(file_path, relative_path)
        
        # Xóa thư mục dự án nếu được yêu cầu
        if delete_after:
            shutil.rmtree(project_dir)
            if project_dir == self.current_project:
                self.current_project = None
        
        return output_path
    
    def rename_project(self, project_dir, new_name):
        """
        Đổi tên dự án
        
        Args:
            project_dir: Đường dẫn thư mục dự án
            new_name: Tên mới cho dự án
            
        Returns:
            Đường dẫn dự án sau khi đổi tên
        """
        if not os.path.exists(project_dir) or not os.path.isdir(project_dir):
            raise FileNotFoundError(f"Không tìm thấy dự án tại '{project_dir}'")
        
        metadata_file = os.path.join(project_dir, "project.json")
        if not os.path.exists(metadata_file):
            raise ValueError(f"Thư mục '{project_dir}' không chứa dự án hợp lệ")
        
        # Đọc metadata
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        
        # Cập nhật tên dự án
        metadata["name"] = new_name
        metadata["last_modified"] = datetime.now().isoformat()
        
        # Ghi lại metadata
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)
        
        # Không đổi tên thư mục vì có thể gây ra nhiều vấn đề với đường dẫn
        return project_dir
    
    def get_folder_files(self, project_dir, folder_name):
        """
        Lấy danh sách các file trong một thư mục của dự án
        
        Args:
            project_dir: Đường dẫn thư mục dự án
            folder_name: Tên thư mục con (images, videos, audio, templates...)
            
        Returns:
            Danh sách các file (đường dẫn đầy đủ)
        """
        folder_path = os.path.join(project_dir, folder_name)
        
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            return []
        
        files = []
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isfile(item_path):
                files.append(item_path)
        
        return sorted(files)
    
    def detect_file_type(self, file_path):
        """
        Tự động phát hiện loại file và thư mục phù hợp để lưu trữ
        
        Args:
            file_path: Đường dẫn file cần phân tích
            
        Returns:
            Tên thư mục phù hợp từ DEFAULT_FOLDERS
        """
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext in self.IMAGE_EXTENSIONS:
            return "images"
        elif ext in self.VIDEO_EXTENSIONS:
            return "videos"
        elif ext in self.AUDIO_EXTENSIONS:
            return "audio"
        elif ext in self.SUBTITLE_EXTENSIONS:
            return "subtitles"
        else:
            # Nếu không xác định được, mặc định là thư mục images
            return "images"
    
    def add_file(self, project_dir, folder_name=None, file_path=""):
        """
        Thêm một file vào thư mục của dự án (sao chép)
        
        Args:
            project_dir: Đường dẫn thư mục dự án
            folder_name: Tên thư mục con (nếu None thì tự động phát hiện)
            file_path: Đường dẫn file muốn thêm
            
        Returns:
            Đường dẫn đến file trong dự án sau khi thêm
        """
        if not os.path.exists(project_dir) or not os.path.isdir(project_dir):
            raise FileNotFoundError(f"Không tìm thấy dự án tại '{project_dir}'")
        
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            raise FileNotFoundError(f"Không tìm thấy file '{file_path}'")
        
        # Nếu không chỉ định thư mục, tự động phát hiện loại file
        if folder_name is None:
            folder_name = self.detect_file_type(file_path)
        
        folder_path = os.path.join(project_dir, folder_name)
        
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        
        # Lấy tên file và đuôi file
        file_basename = os.path.basename(file_path)
        
        # Tạo đường dẫn mới trong dự án
        new_file_path = os.path.join(folder_path, file_basename)
        
        # Kiểm tra nếu file đã tồn tại trong dự án, thêm số đằng sau để không bị trùng
        counter = 1
        while os.path.exists(new_file_path):
            name, ext = os.path.splitext(file_basename)
            new_file_path = os.path.join(folder_path, f"{name}_{counter}{ext}")
            counter += 1
        
        # Sao chép file
        shutil.copy2(file_path, new_file_path)
        
        return new_file_path
    
    def rename_file(self, file_path, new_name):
        """
        Đổi tên một file trong dự án
        
        Args:
            file_path: Đường dẫn file cần đổi tên
            new_name: Tên mới (không bao gồm đường dẫn)
            
        Returns:
            Đường dẫn mới của file sau khi đổi tên
        """
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            raise FileNotFoundError(f"Không tìm thấy file '{file_path}'")
        
        # Xử lý tên file để tránh ký tự không hợp lệ
        safe_name = self._sanitize_filename(new_name)
        if not safe_name:
            raise ValueError("Tên file không hợp lệ")
        
        # Giữ lại đuôi file
        _, ext = os.path.splitext(file_path)
        if not "." in safe_name:
            safe_name = safe_name + ext
        
        # Tính đường dẫn mới
        dir_path = os.path.dirname(file_path)
        new_file_path = os.path.join(dir_path, safe_name)
        
        # Kiểm tra xem file đã tồn tại chưa
        counter = 1
        while os.path.exists(new_file_path) and new_file_path != file_path:
            name, ext = os.path.splitext(safe_name)
            new_file_path = os.path.join(dir_path, f"{name}_{counter}{ext}")
            counter += 1
        
        # Đổi tên file
        os.rename(file_path, new_file_path)
        
        return new_file_path
    
    def delete_file(self, file_path):
        """
        Xóa một file từ dự án
        
        Args:
            file_path: Đường dẫn file cần xóa
        """
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            raise FileNotFoundError(f"Không tìm thấy file '{file_path}'")
        
        os.remove(file_path)
    
    def organize_project_folder(self, project_dir):
        """
        Tự động sắp xếp các file trong thư mục gốc của dự án vào các thư mục con phù hợp
        
        Args:
            project_dir: Đường dẫn thư mục dự án
            
        Returns:
            Dict với kết quả phân loại: {folder_name: [file_paths]}
        """
        if not os.path.exists(project_dir) or not os.path.isdir(project_dir):
            raise FileNotFoundError(f"Không tìm thấy dự án tại '{project_dir}'")
        
        # Xác thực đây là thư mục dự án hợp lệ
        metadata_file = os.path.join(project_dir, "project.json")
        if not os.path.exists(metadata_file):
            raise ValueError(f"Thư mục '{project_dir}' không phải là dự án hợp lệ")
        
        # Đọc metadata để lấy thông tin về các thư mục
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        
        # Đảm bảo tất cả các thư mục con tồn tại
        folder_paths = {}
        for folder_name in metadata["folders"]:
            folder_path = os.path.join(project_dir, folder_name)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            folder_paths[folder_name] = folder_path
        
        # Tìm tất cả các file trong thư mục gốc
        result = {folder: [] for folder in metadata["folders"]}
        for item in os.listdir(project_dir):
            item_path = os.path.join(project_dir, item)
            
            # Bỏ qua các thư mục và file project.json
            if os.path.isdir(item_path) or item == "project.json":
                continue
            
            # Xác định loại file và thư mục phù hợp
            folder_name = self.detect_file_type(item_path)
            
            # Di chuyển file vào thư mục phù hợp
            target_folder = folder_paths.get(folder_name)
            if target_folder:
                # Tạo đường dẫn đích
                target_path = os.path.join(target_folder, item)
                
                # Kiểm tra xem file đã tồn tại chưa
                counter = 1
                base_name, ext = os.path.splitext(item)
                while os.path.exists(target_path):
                    target_path = os.path.join(target_folder, f"{base_name}_{counter}{ext}")
                    counter += 1
                
                # Di chuyển file
                shutil.move(item_path, target_path)
                result[folder_name].append(target_path)
        
        return result
    
    def _sanitize_filename(self, filename):
        """
        Xử lý tên file để đảm bảo không có ký tự không hợp lệ
        
        Args:
            filename: Tên file cần xử lý
            
        Returns:
            Tên file đã được xử lý
        """
        # Loại bỏ ký tự không hợp lệ
        s = re.sub(r'[\\/*?:"<>|]', "", filename)
        # Loại bỏ khoảng trắng đầu và cuối
        s = s.strip()
        # Thay thế nhiều khoảng trắng liên tiếp bằng một khoảng trắng
        s = re.sub(r'\s+', " ", s)
        return s
