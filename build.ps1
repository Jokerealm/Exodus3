$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
python -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
& '.\.venv\Scripts\python.exe' -m PyInstaller --noconfirm --distpath dist --workpath build "$PSScriptRoot\Exodus3BankEditor.spec"
