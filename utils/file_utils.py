import os
import time
from PyQt5.QtWidgets import QMessageBox

def check_file_exists(filepath, is_video=True):
    """
    Check if a file already exists and return appropriate action
    Returns:
        - 'overwrite' to replace existing file
        - 'rename' to auto-rename the new file
        - 'skip' to abort the download
        - None if file doesn't exist
    """
    if os.path.exists(filepath):
        return True
    return False

def handle_duplicate_file(filepath, parent_window=None):
    """
    Handle case where file already exists
    Returns:
        - 'overwrite' to replace existing file
        - 'rename' to auto-rename the new file
        - 'skip' to abort the download
        - None if user cancels
    """
    if not parent_window:
        # Default to rename when no UI is available
        return 'rename'
    
    msg = QMessageBox(parent_window)
    msg.setWindowTitle("File Already Exists")
    msg.setText(f"The file already exists:\n{os.path.basename(filepath)}")
    msg.setInformativeText("What would you like to do?")
    msg.setIcon(QMessageBox.Warning)
    
    overwrite_button = msg.addButton("Overwrite", QMessageBox.AcceptRole)
    rename_button = msg.addButton("Auto-Rename", QMessageBox.AcceptRole)
    skip_button = msg.addButton("Skip", QMessageBox.RejectRole)
    
    msg.exec_()
    
    clicked_button = msg.clickedButton()
    
    if clicked_button == overwrite_button:
        return 'overwrite'
    elif clicked_button == rename_button:
        return 'rename'
    elif clicked_button == skip_button:
        return 'skip'
    else:
        return None

def generate_unique_filename(filepath):
    """Generate a unique filename by adding timestamp"""
    dir_path, filename = os.path.split(filepath)
    base_name, ext = os.path.splitext(filename)
    
    # Add timestamp
    timestamp = int(time.time())
    new_filename = f"{base_name}_{timestamp}{ext}"
    new_filepath = os.path.join(dir_path, new_filename)
    
    # If somehow still exists, keep adding numbers until unique
    counter = 1
    while os.path.exists(new_filepath):
        new_filename = f"{base_name}_{timestamp}_{counter}{ext}"
        new_filepath = os.path.join(dir_path, new_filename)
        counter += 1
    
    return new_filepath
