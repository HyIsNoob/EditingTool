import os
import sys
import subprocess
import shutil
from pathlib import Path

def main():
    """Create an installer for the application"""
    print("Creating installer for KHyTool...")
    
    # Verify NSIS is installed
    nsis_path = find_nsis()
    if not nsis_path:
        print("NSIS (Nullsoft Scriptable Install System) not found.")
        print("Please install NSIS from https://nsis.sourceforge.io/Download")
        return False
    
    # Application information
    app_name = "KHyTool"
    app_version = "1.0.0"
    app_publisher = "KHyTool Team"
    app_url = "https://example.com/khytool"
    
    # Directory locations
    dist_dir = os.path.join(os.getcwd(), 'dist', 'KHyTool')
    installer_dir = os.path.join(os.getcwd(), 'installer')
    nsis_script = os.path.join(installer_dir, 'installer_script.nsi')
    
    # Create installer directory if it doesn't exist
    os.makedirs(installer_dir, exist_ok=True)
    
    # Generate NSIS script
    print("Generating NSIS installation script...")
    with open(nsis_script, 'w') as script:
        script.write(f'''
; KHyTool Installer Script
Unicode True

!define APP_NAME "{app_name}"
!define APP_VERSION "{app_version}"
!define APP_PUBLISHER "{app_publisher}"
!define APP_URL "{app_url}"

Name "${{APP_NAME}} ${{APP_VERSION}}"
OutFile "{installer_dir}\\{app_name}_Setup.exe"

; Default installation directory
InstallDir "$PROGRAMFILES64\\{app_name}"

; Request application privileges
RequestExecutionLevel admin

;--------------------------------
; Interface Settings
!include "MUI2.nsh"

!define MUI_ABORTWARNING
!define MUI_ICON "{dist_dir}\\resources\\app_icon.ico"
!define MUI_UNICON "{dist_dir}\\resources\\app_icon.ico"

;--------------------------------
; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "{dist_dir}\\README.md"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
; Languages
!insertmacro MUI_LANGUAGE "English"

;--------------------------------
; Installer Sections
Section "Install"
    SetOutPath "$INSTDIR"
    
    ; Include all files from dist directory
    File /r "{dist_dir}\\*.*"
    
    ; Create downloads directory with write permissions for all users
    CreateDirectory "$INSTDIR\\downloads"
    AccessControl::GrantOnFile "$INSTDIR\\downloads" "(BU)" "FullAccess"
    
    ; Create thumbnails directory with write permissions for all users
    CreateDirectory "$INSTDIR\\thumbnails"
    AccessControl::GrantOnFile "$INSTDIR\\thumbnails" "(BU)" "FullAccess"
    
    ; Create config directory with write permissions for all users
    CreateDirectory "$INSTDIR\\config"
    AccessControl::GrantOnFile "$INSTDIR\\config" "(BU)" "FullAccess"
    
    ; Create Start Menu shortcut with admin flag
    CreateDirectory "$SMPROGRAMS\\{app_name}"
    CreateShortcut "$SMPROGRAMS\\{app_name}\\{app_name}.lnk" "$INSTDIR\\{app_name}.exe"
    FileOpen $0 "$SMPROGRAMS\\{app_name}\\{app_name}.lnk" a
    FileSeek $0 0 END
    FileWrite $0 " " ; Admin flag - this marks the shortcut to request elevation
    FileClose $0
    
    CreateShortcut "$SMPROGRAMS\\{app_name}\\Uninstall.lnk" "$INSTDIR\\uninstall.exe"
    
    ; Create Desktop shortcut with admin flag
    CreateShortcut "$DESKTOP\\{app_name}.lnk" "$INSTDIR\\{app_name}.exe"
    FileOpen $0 "$DESKTOP\\{app_name}.lnk" a
    FileSeek $0 0 END
    FileWrite $0 " " ; Admin flag - this marks the shortcut to request elevation
    FileClose $0
    
    ; Write uninstaller
    WriteUninstaller "$INSTDIR\\uninstall.exe"
    
    ; Write registry keys for uninstall information
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}" "DisplayName" "{app_name} - Video and Text Processing Tool"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}" "UninstallString" "$\\"$INSTDIR\\uninstall.exe$\\""
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}" "DisplayVersion" "{app_version}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}" "Publisher" "{app_publisher}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}" "URLInfoAbout" "{app_url}"
    
    ; Register ffmpeg and ensure it can be found by the application
    ExecWait 'setx PATH "%PATH%;$INSTDIR" /M'
SectionEnd

;--------------------------------
; Uninstaller Section
Section "Uninstall"
    ; Remove Start Menu shortcuts
    Delete "$SMPROGRAMS\\{app_name}\\{app_name}.lnk"
    Delete "$SMPROGRAMS\\{app_name}\\Uninstall.lnk"
    RMDir "$SMPROGRAMS\\{app_name}"
    
    ; Remove Desktop shortcut
    Delete "$DESKTOP\\{app_name}.lnk"
    
    ; Remove files
    RMDir /r "$INSTDIR\\*.*"
    
    ; Remove registry keys
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}"
    
    ; Remove installation directory (if empty)
    RMDir "$INSTDIR"
SectionEnd
''')
    
    # Run NSIS to create installer
    print("Running NSIS to build installer...")
    result = subprocess.run([nsis_path, nsis_script], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error creating installer: {result.stderr}")
        return False
    
    print(f"Installer created successfully: {installer_dir}\\{app_name}_Setup.exe")
    return True

def find_nsis():
    """Find the NSIS executable on the system"""
    # Common paths
    nsis_paths = [
        r"C:\Program Files (x86)\NSIS\makensis.exe",
        r"C:\Program Files\NSIS\makensis.exe",
    ]
    
    # Check environment path
    try:
        result = subprocess.run(["where", "makensis"], capture_output=True, text=True)
        if result.returncode == 0:
            path = result.stdout.strip().split('\n')[0]
            if path:
                return path
    except Exception:
        pass
    
    # Check common installation paths
    for path in nsis_paths:
        if os.path.exists(path):
            return path
    
    return None

if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
