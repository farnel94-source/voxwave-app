# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec pour VoxWave (multi-plateforme)."""

import os
import sys

block_cipher = None

# Repertoire racine du projet
ROOT = os.path.dirname(os.path.abspath(SPEC))

# Detection plateforme
is_linux = sys.platform == "linux"
is_windows = sys.platform == "win32"
is_darwin = sys.platform == "darwin"

# Icone : .ico pour Windows, .png pour Linux, .icns pour macOS
icon_file = None
if is_windows:
    ico_path = os.path.join(ROOT, 'assets', 'icon.ico')
    if os.path.exists(ico_path):
        icon_file = ico_path
elif is_darwin:
    icns_path = os.path.join(ROOT, 'assets', 'icon.icns')
    if os.path.exists(icns_path):
        icon_file = icns_path

a = Analysis(
    [os.path.join(ROOT, 'src', '__main__.py')],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join(ROOT, 'config.yaml'), '.'),
        (os.path.join(ROOT, '.env.example'), '.'),
        (os.path.join(ROOT, 'src', 'gui', 'orb'), 'src/gui/orb'),
        (os.path.join(ROOT, 'THIRD_PARTY_LICENSES.txt'), '.'),
        (os.path.join(ROOT, 'LICENSE'), '.'),
    ],
    hiddenimports=[
        'faster_whisper',
        'sounddevice',
        'numpy',
        'groq',
        'openai',
        # PySide6
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebChannel',
        'PySide6.QtWebEngineCore',
        'shiboken6',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'cryptography',
        'cryptography.fernet',
        'pynput',
        'pynput.keyboard',
        'evdev',
        'pyperclip',
        'keyboard',
        'yaml',
        'click',
        'requests',
        'dotenv',
        'src',
        'src.app',
        'src.audio',
        'src.audio.capture',
        'src.audio.processor',
        'src.audio.feedback',
        'src.audio.device_manager',
        'src.transcription',
        'src.transcription.whisper_engine',
        'src.transcription.groq_engine',
        'src.transcription.hybrid_engine',
        'src.cleaning',
        'src.cleaning.regex_cleaner',
        'src.cleaning.llm_cleaner',
        'src.injection',
        'src.injection.keyboard',
        'src.hotkey',
        'src.hotkey.listener',
        'src.gui',
        'src.gui.icons',
        'src.gui.tray_icon',
        'src.gui.waveform_widget',
        'src.config',
        'src.config.defaults',
        'src.config.validator',
        'src.utils',
        'src.utils.retry',
        'src.utils.exceptions',
        'src.utils.platform',
        'src.licensing',
        'src.licensing.lemonsqueezy',
        'src.licensing.storage',
        'src.licensing.validator',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'pandas',
        'pytest',
        'black',
        'flake8',
        'pystray',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VoxWave',
    debug=False,
    bootloader_ignore_signals=False,
    strip=is_linux,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)

# onedir : les DLLs/SO restent separees (obligation LGPL pour PySide6 et pynput)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=is_linux,
    upx=True,
    upx_exclude=[],
    name='VoxWave',
)
