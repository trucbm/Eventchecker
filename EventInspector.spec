# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules


# The bundled Services Checker only needs binary-XML parsing. Collecting the
# whole package also imports the optional pentest/frida modules and breaks
# PyInstaller builds when frida is not installed.
androguard_hiddenimports = collect_submodules('androguard.core')

# Keep runtime-generated uploads and extracted files out of the packaged app.
services_checker_datas = [
    ('services_checker/app.py', 'services_checker'),
    ('services_checker/bundletool-all-1.18.1.jar', 'services_checker'),
    ('services_checker/apk_check_presets.json', 'services_checker'),
    ('services_checker/gradle_check_presets.json', 'services_checker'),
    ('services_checker/podfile_check_presets.json', 'services_checker'),
    ('services_checker/manifest_check_presets.json', 'services_checker'),
    ('services_checker/my-key.keystore', 'services_checker'),
]

a = Analysis(
    ['desktop_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('Log_checker.py', '.'),
        ('Default event + Default Params.xlsx', '.'),
        ('sdk_check_presets.json', '.'),
        ('remote_update_config_v250.json', '.'),
        *services_checker_datas,
    ],
    hiddenimports=['engineio.async_drivers.threading', *androguard_hiddenimports],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['markupsafe._speedups'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='EventInspector',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='universal2',
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/app.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='EventInspector',
)
app = BUNDLE(
    coll,
    name='EventInspector.app',
    icon='assets/app.icns',
    bundle_identifier=None,
)
