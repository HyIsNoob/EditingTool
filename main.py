import sys
import os
import traceback
from PyQt5.QtWidgets import QApplication, QMessageBox

# Ensure bin directory is in PATH
bin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")
if os.path.exists(bin_dir):
    os.environ["PATH"] = bin_dir + os.pathsep + os.environ["PATH"]

# Make sure utils is importable for the compatibility layer
if not os.path.dirname(os.path.abspath(__file__)) in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Run environment checks first
try:
    from runtime_checks import check_environment
    env_status = check_environment()
except ImportError:
    # Handle case where runtime_checks might not be available
    env_status = {"ffmpeg": {"available": False}}

# Initialize compatibility layer 
from utils import compat

# Import MainMenu after compatibility is set up
from ui.main_menu import MainMenu

def main():
    app = QApplication([])
    
    # Show warning if FFmpeg is not available
    if not env_status["ffmpeg"]["available"]:
        QMessageBox.warning(
            None, 
            "FFmpeg Not Found", 
            "FFmpeg is not available. Some features may not work correctly.\n\n"
            "If you experience issues with video or audio processing,\n"
            "please reinstall the application or contact support."
        )
    
    main_menu = MainMenu()
    main_menu.show()
    app.exec_()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Show error dialog for uncaught exceptions
        error_msg = f"An unexpected error occurred:\n\n{str(e)}\n\n{traceback.format_exc()}"
        QMessageBox.critical(None, "Error", error_msg)
        raise
