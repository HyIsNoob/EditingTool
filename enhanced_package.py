import os
import sys
import shutil
import subprocess
import platform
import glob
from pathlib import Path

def get_app_dir():
    """Get the application directory"""
    return os.path.dirname(os.path.abspath(__file__))

def create_folders():
    """Create necessary folders for packaging"""
    folders = [
        "resources/icons",
        "bin",
        "models/whisper"
    ]
    
    for folder in folders:
        folder_path = os.path.join(get_app_dir(), folder)
        os.makedirs(folder_path, exist_ok=True)
        print(f"Created folder: {folder}")

def download_ffmpeg():
    """Download FFmpeg binaries"""
    from utils.ffmpeg_manager import FFmpegManager
    
    print("Downloading FFmpeg binaries...")
    ffmpeg_manager = FFmpegManager()
    success = ffmpeg_manager.download_ffmpeg()
    
    if success:
        print("FFmpeg binaries downloaded successfully")
        
        # Make sure to include the FFmpeg binaries in the bin directory
        app_dir = get_app_dir()
        bin_dir = os.path.join(app_dir, "bin")
        
        if not os.path.exists(bin_dir):
            os.makedirs(bin_dir)
        
        # Get paths to FFmpeg binaries
        ffmpeg_path = ffmpeg_manager.get_ffmpeg_path()
        ffprobe_path = ffmpeg_manager.get_ffprobe_path()
        
        if ffmpeg_path and os.path.exists(ffmpeg_path):
            # Copy FFmpeg binary to the bin directory for packaging
            dest_path = os.path.join(bin_dir, os.path.basename(ffmpeg_path))
            shutil.copy2(ffmpeg_path, dest_path)
            print(f"Copied FFmpeg to {dest_path}")
        
        if ffprobe_path and os.path.exists(ffprobe_path):
            # Copy FFprobe binary to the bin directory for packaging
            dest_path = os.path.join(bin_dir, os.path.basename(ffprobe_path))
            shutil.copy2(ffprobe_path, dest_path)
            print(f"Copied FFprobe to {dest_path}")
    else:
        print("Failed to download FFmpeg. Package may not work correctly.")

def create_spec_file():
    """Create a PyInstaller spec file"""
    app_dir = get_app_dir()
    spec_path = os.path.join(app_dir, "KHyTool.spec")
    
    # Name of the executable
    app_name = "KHyTool"
    
    # Path to the icon file
    icon_path = os.path.join(app_dir, "resources", "icons", "app_icon.ico")
    icon_option = f"icon='{icon_path.replace(os.sep, '/')}'" if os.path.exists(icon_path) else ""
    
    print(f"Creating spec file: {spec_path}")
    
    with open(spec_path, "w") as f:
        f.write(f"""# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Set block cipher to None for no encryption
block_cipher = None

# Collect all necessary data files
datas = [
    ('resources', 'resources'),
    ('bin', 'bin'),
    ('models', 'models')
]

# List of hidden modules that might not be detected automatically
hidden_imports = [
    # UI modules
    'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets',
    
    # Video/image processing
    'cv2', 'numpy', 'PIL',
    
    # Download functionality
    'yt_dlp', 'yt_dlp.extractor', 
    
    # Project modules
    'ui', 'project', 'utils',
]

# Add all project submodules dynamically
hidden_imports.extend(collect_submodules('ui'))
hidden_imports.extend(collect_submodules('project'))
hidden_imports.extend(collect_submodules('utils'))

# Create the Analysis object with all imports and data files
a = Analysis(
    ['main.py'],  # Main script
    pathex=['{app_dir}'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Create the PYZ archive
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Create the executable
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{app_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    {icon_option}
)

# Create the directory structure
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='{app_name}'
)
""")
    
    return spec_path

def clean_previous_builds():
    """Remove previous build folders"""
    for folder in ['build', 'dist']:
        folder_path = os.path.join(get_app_dir(), folder)
        if os.path.exists(folder_path):
            print(f"Cleaning {folder} directory...")
            shutil.rmtree(folder_path)

def install_dependencies():
    """Make sure all necessary Python packages are installed"""
    print("Installing required Python packages...")
    
    requirements = [
        "PyQt5", "Pillow", "numpy", "yt-dlp", "pyinstaller",
    ]
    
    for package in requirements:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"Installed {package}")
        except subprocess.CalledProcessError:
            print(f"Failed to install {package}")

def run_pyinstaller(spec_file):
    """Run PyInstaller with the spec file"""
    print("Running PyInstaller...")
    
    pyinstaller_cmd = ["pyinstaller", "--clean", spec_file]
    subprocess.call(pyinstaller_cmd)

def copy_additional_files():
    """Copy additional files to the dist folder"""
    # For example, copy a README or license file
    app_dir = get_app_dir()
    dist_dir = os.path.join(app_dir, "dist", "KHyTool")
    
    files_to_copy = {
        # "README.md": "README.md",
        # "LICENSE": "LICENSE",
    }
    
    for src, dst in files_to_copy.items():
        src_path = os.path.join(app_dir, src)
        dst_path = os.path.join(dist_dir, dst)
        if os.path.exists(src_path):
            shutil.copy2(src_path, dst_path)
            print(f"Copied {src} to {dst_path}")

def enhance_package():
    """Enhance the PyInstaller package with additional files and configurations"""
    print("Enhancing PyInstaller package...")
    
    # Define paths
    dist_dir = os.path.join(os.getcwd(), 'dist', 'KHyTool')
    if not os.path.exists(dist_dir):
        print(f"Error: Distribution directory '{dist_dir}' not found.")
        return False
    
    # Create necessary directories if they don't exist
    os.makedirs(os.path.join(dist_dir, 'downloads'), exist_ok=True)
    os.makedirs(os.path.join(dist_dir, 'thumbnails'), exist_ok=True)
    os.makedirs(os.path.join(dist_dir, 'temp'), exist_ok=True)
    os.makedirs(os.path.join(dist_dir, 'resources'), exist_ok=True)  # Ensure resources directory exists

    # Copy the icon file to the resources directory in the dist folder
    icon_src = os.path.join(os.getcwd(), 'resources', 'icon.ico')
    icon_dest = os.path.join(dist_dir, 'resources', 'icon.ico')
    if os.path.exists(icon_src):
        shutil.copy2(icon_src, icon_dest)
        print(f"Copied icon file to {icon_dest}")
    else:
        print(f"Warning: Icon file not found at {icon_src}. Installer may fail.")
    
    # Copy over ffmpeg binaries if they exist in the system
    ffmpeg_paths = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'ffmpeg', 'bin', 'ffmpeg.exe'),
    ]
    
    # Try to find ffmpeg in PATH
    try:
        result = subprocess.run(["where", "ffmpeg"], capture_output=True, text=True)
        if result.returncode == 0:
            path_ffmpeg = result.stdout.strip().split('\n')[0]
            if path_ffmpeg:
                ffmpeg_paths.insert(0, path_ffmpeg)
    except Exception as e:
        print(f"Could not check ffmpeg in PATH: {e}")
    
    # Copy the first found ffmpeg
    ffmpeg_copied = False
    for ffmpeg_path in ffmpeg_paths:
        if os.path.exists(ffmpeg_path):
            print(f"Found ffmpeg at: {ffmpeg_path}")
            try:
                shutil.copy2(ffmpeg_path, os.path.join(dist_dir, 'ffmpeg.exe'))
                ffmpeg_copied = True
                print("Copied ffmpeg.exe to distribution directory")
                break
            except Exception as e:
                print(f"Failed to copy ffmpeg: {e}")
    
    if not ffmpeg_copied:
        print("Warning: Could not find ffmpeg.exe. Audio processing may not work correctly.")
    
    # Copy application README and documentation
    readme_path = os.path.join(os.getcwd(), 'README.md')
    if os.path.exists(readme_path):
        shutil.copy2(readme_path, os.path.join(dist_dir, 'README.md'))
        print("Copied README.md to distribution directory")
    
    # Create default configuration file if it doesn't exist
    config_dir = os.path.join(dist_dir, 'config')
    os.makedirs(config_dir, exist_ok=True)
    default_config = os.path.join(config_dir, 'settings.json')
    if not os.path.exists(default_config):
        # Create a basic settings file
        with open(default_config, 'w', encoding='utf-8') as f:
            f.write('{\n')
            f.write('    "output_directory": "~/Downloads",\n')
            f.write('    "language": "en",\n')
            f.write('    "theme": "light",\n')
            f.write('    "save_thumbnails": true,\n')
            f.write('    "auto_update_check": true\n')
            f.write('}\n')
        print("Created default configuration file")
    
    # Create downloads persistence file to store download history
    downloads_db = os.path.join(config_dir, 'downloads.json')
    if not os.path.exists(downloads_db):
        with open(downloads_db, 'w', encoding='utf-8') as f:
            f.write('[]')
        print("Created downloads persistence file")
    
    # Add runtime checks script to verify dependencies at startup
    shutil.copy2(os.path.join(os.getcwd(), 'runtime_checks.py'), 
                os.path.join(dist_dir, 'runtime_checks.py'))
    print("Added runtime checks script")
    
    # Copy and configure any other necessary files for downloaders
    # Create a default README with usage instructions
    download_readme = os.path.join(dist_dir, 'downloads', 'README.txt')
    with open(download_readme, 'w', encoding='utf-8') as f:
        f.write("Downloaded files will be saved in this directory by default.\n")
        f.write("You can change the download location in the application settings.\n")
    
    print("Enhanced package successfully")
    return True

def package_app():
    """Main function to package the application"""
    print("=== PACKAGING KHYTOOL APPLICATION ===")
    
    # Preparation steps
    create_folders()
    clean_previous_builds()
    install_dependencies()
    
    # Download FFmpeg
    try:
        download_ffmpeg()
    except Exception as e:
        print(f"Warning: Failed to download FFmpeg: {e}")
        print("You may need to manually copy FFmpeg binaries to the bin folder.")
    
    # Create and run PyInstaller spec
    spec_file = create_spec_file()
    run_pyinstaller(spec_file)
    
    # Post-build steps
    copy_additional_files()
    enhance_package()
    
    # Done
    dist_dir = os.path.join(get_app_dir(), "dist", "KHyTool")
    print("\nPackaging complete!")
    print(f"Application packaged to: {dist_dir}")
    print("You can now create an installer with Inno Setup.")

if __name__ == "__main__":
    package_app()
