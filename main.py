import sys
import os
import traceback
from PyQt5.QtWidgets import QApplication, QMessageBox, QDialog
from PyQt5.QtCore import QTimer

# Ensure bin directory is in PATH
bin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")
if os.path.exists(bin_dir):
    os.environ["PATH"] = bin_dir + os.pathsep + os.environ["PATH"]

# Make sure utils is importable for the compatibility layer
if not os.path.dirname(os.path.abspath(__file__)) in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Define application constants
APP_VERSION = "1.1.0"
GITHUB_REPO = "HyIsNoob/EditingTool"  # Replace with actual GitHub repo

# Run environment checks first
try:
    from runtime_checks import check_environment
    env_status = check_environment()
except ImportError:
    # Handle case where runtime_checks might not be available
    env_status = {"ffmpeg": {"available": False}}

# Initialize compatibility layer 
from utils import compat

# Import updater components
try:
    from utils.updater import Updater
    from ui.update_dialog import UpdateDialog
except ImportError:
    # Fallback if updater module isn't available
    Updater = None

# Import MainMenu after compatibility is set up
from ui.main_menu import MainMenu

def check_for_updates(main_window):
    """Check for application updates"""
    if Updater is None:
        return
        
    try:
        updater = Updater(GITHUB_REPO, APP_VERSION)
        
        def on_update_available(new_version, release_notes):
            dialog = UpdateDialog(new_version, APP_VERSION, release_notes, parent=main_window)
            
            # Connect updater signals to dialog
            updater.update_progress.connect(dialog.update_progress)
            updater.update_completed.connect(dialog.update_finished)
            
            result = dialog.exec_()
            
            if result == QDialog.Accepted:
                updater.download_and_install_update()
        
        # Connect signal and start the check
        updater.update_available.connect(on_update_available)
        
        # Use a timer to allow the UI to initialize first
        QTimer.singleShot(2000, updater.check_for_updates)
    
    except Exception as e:
        # Just log errors, don't interrupt application startup
        print(f"Error checking for updates: {str(e)}")

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
    
    # Check for updates after window is shown
    check_for_updates(main_menu)
    
    app.exec_()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Show error dialog for uncaught exceptions
        error_msg = f"An unexpected error occurred:\n\n{str(e)}\n\n{traceback.format_exc()}"
        QMessageBox.critical(None, "Error", error_msg)
        raise
