
; KHyTool Installer Script
Unicode True

!define APP_NAME "KHyTool"
!define APP_VERSION "1.0.0"
!define APP_PUBLISHER "KHyTool Team"
!define APP_URL "https://example.com/khytool"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "D:\fileluu\Tools\ProjectPic2Text\installer\KHyTool_Setup.exe"

; Default installation directory
InstallDir "$PROGRAMFILES64\KHyTool"

; Request application privileges
RequestExecutionLevel admin

;--------------------------------
; Interface Settings
!include "MUI2.nsh"

!define MUI_ABORTWARNING
!define MUI_ICON "D:\fileluu\Tools\ProjectPic2Text\dist\KHyTool\resources\app_icon.ico"
!define MUI_UNICON "D:\fileluu\Tools\ProjectPic2Text\dist\KHyTool\resources\app_icon.ico"

;--------------------------------
; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "D:\fileluu\Tools\ProjectPic2Text\dist\KHyTool\README.md"
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
    File /r "D:\fileluu\Tools\ProjectPic2Text\dist\KHyTool\*.*"
    
    ; Create downloads directory with write permissions for all users
    CreateDirectory "$INSTDIR\downloads"
    AccessControl::GrantOnFile "$INSTDIR\downloads" "(BU)" "FullAccess"
    
    ; Create thumbnails directory with write permissions for all users
    CreateDirectory "$INSTDIR\thumbnails"
    AccessControl::GrantOnFile "$INSTDIR\thumbnails" "(BU)" "FullAccess"
    
    ; Create config directory with write permissions for all users
    CreateDirectory "$INSTDIR\config"
    AccessControl::GrantOnFile "$INSTDIR\config" "(BU)" "FullAccess"
    
    ; Create Start Menu shortcut
    CreateDirectory "$SMPROGRAMS\KHyTool"
    CreateShortcut "$SMPROGRAMS\KHyTool\KHyTool.lnk" "$INSTDIR\KHyTool.exe"
    CreateShortcut "$SMPROGRAMS\KHyTool\Uninstall.lnk" "$INSTDIR\uninstall.exe"
    
    ; Create Desktop shortcut
    CreateShortcut "$DESKTOP\KHyTool.lnk" "$INSTDIR\KHyTool.exe"
    
    ; Write uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"
    
    ; Write registry keys for uninstall information
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\KHyTool" "DisplayName" "KHyTool - Video and Text Processing Tool"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\KHyTool" "UninstallString" "$\"$INSTDIR\uninstall.exe$\""
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\KHyTool" "DisplayVersion" "1.0.0"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\KHyTool" "Publisher" "KHyTool Team"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\KHyTool" "URLInfoAbout" "https://example.com/khytool"
    
    ; Register ffmpeg and ensure it can be found by the application
    ExecWait 'setx PATH "%PATH%;$INSTDIR" /M'
SectionEnd

;--------------------------------
; Uninstaller Section
Section "Uninstall"
    ; Remove Start Menu shortcuts
    Delete "$SMPROGRAMS\KHyTool\KHyTool.lnk"
    Delete "$SMPROGRAMS\KHyTool\Uninstall.lnk"
    RMDir "$SMPROGRAMS\KHyTool"
    
    ; Remove Desktop shortcut
    Delete "$DESKTOP\KHyTool.lnk"
    
    ; Remove files
    RMDir /r "$INSTDIR\*.*"
    
    ; Remove registry keys
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\KHyTool"
    
    ; Remove installation directory (if empty)
    RMDir "$INSTDIR"
SectionEnd
