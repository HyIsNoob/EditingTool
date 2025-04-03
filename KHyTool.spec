# -*- mode: python ; coding: utf-8 -*-

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
    pathex=['D:\fileluu\Tools\EditingTool'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
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
    name='KHyTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    icon='D:/fileluu/Tools/EditingTool/resources/icons/app_icon.ico',
    uac_admin=True,  # Request admin rights when launching
    uac_uiAccess=False,
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
    name='KHyTool'
)
