# Build with Python 3.12 on Windows 64-bit.
from pathlib import Path
src = Path(SPECPATH)
a = Analysis([str(src / 'app.py')], pathex=[str(src)], binaries=[],
    datas=[(str(src / 'assets'), 'assets')], hiddenimports=[], hookspath=[],
    hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False, optimize=0)
# Qt links Windows ICU; do not pick up an incompatible ICU from an inherited PATH.
a.binaries = [entry for entry in a.binaries if Path(entry[1]).name.lower() != 'icuuc.dll']
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='Exodus3BankEditor',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, icon=[str(src / 'assets' / 'icon.ico')])
