
; KHyTool Installer Script
!include "MUI2.nsh"

; General
Name "KHyTool"
OutFile "KHyTool_Setup.exe"
InstallDir "$PROGRAMFILES\KHyTool"
InstallDirRegKey HKCU "Software\KHyTool" "Install_Dir"

RequestExecutionLevel admin

; Interface Settings
!define MUI_ABORTWARNING


; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Language
!insertmacro MUI_LANGUAGE "English"

; Install sections
Section "KHyTool" SecMain
    SetOutPath "$INSTDIR"
    
    ; Files to install
    File /r "D:\fileluu\Tools\ProjectPic2Text\dist\KHyTool\*.*"
    
    ; Include FFmpeg
    File "D:\fileluu\Tools\ProjectPic2Text\bin\ffmpeg.exe"

    ; Create shortcuts
    CreateDirectory "$SMPROGRAMS\KHyTool"
    CreateShortcut "$SMPROGRAMS\KHyTool\KHyTool.lnk" "$INSTDIR\KHyTool.exe"
    CreateShortcut "$DESKTOP\KHyTool.lnk" "$INSTDIR\KHyTool.exe"
    
    ; Write registry keys for uninstaller
    WriteRegStr HKCU "Software\KHyTool" "Install_Dir" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\KHyTool" "DisplayName" "KHyTool"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\KHyTool" "UninstallString" '"$INSTDIR\uninstall.exe"'
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

; Uninstaller section
Section "Uninstall"
    ; Remove files and directories
    Delete "$INSTDIR\uninstall.exe"
    RMDir /r "$INSTDIR"
    
    ; Remove shortcuts
    Delete "$SMPROGRAMS\KHyTool\KHyTool.lnk"
    RMDir "$SMPROGRAMS\KHyTool"
    Delete "$DESKTOP\KHyTool.lnk"
    
    ; Remove registry keys
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\KHyTool"
    DeleteRegKey HKCU "Software\KHyTool"
SectionEnd
