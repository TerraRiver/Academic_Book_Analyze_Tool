# build_config.spec
# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

# 项目根目录
project_root = os.getcwd()

block_cipher = None

a = Analysis(
    ['main.py'],  # 主入口文件
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        # 包含UI文件
        ('ui/*.py', 'ui'),
        # 包含核心模块
        ('core/*.py', 'core'),
        # 包含资源文件
        ('assets', 'assets'),
        # 包含配置文件模板
        ('config.ini', '.'),
        # 如果使用了其他数据文件，也要包含
    ],
    hiddenimports=[
        # 动态导入的模块需要手动指定
        'ui.main_window',
        'ui.settings_dialog',
        'core.book_manager',
        'core.pdf_processor',
        'core.api_handler',
        'core.report_generator',
        'json_to_markdown',
        # 常见的隐藏依赖
        'requests',
        'json',
        'asyncio',
        'configparser',
        'pathlib',
        'os',
        'pypdf',
        'python-docx',
        # PySide6
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtSvg',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TR_book_reader',  # exe文件名
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 设为False隐藏控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icons/app_icon.ico'  # 应用图标（可选）
)
