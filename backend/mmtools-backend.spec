# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src/server.py'],
    pathex=[],
    binaries=[],
    datas=[('data/Sample_Data.json', 'data'), ('src/mm_to_json/jre', 'mm_to_json/jre'), ('src/mm_to_json/lib', 'mm_to_json/lib'), ('src/mm_to_json/reporting/templates', 'mm_to_json/reporting/templates')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='mmtools-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
