cd ..\
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --onefile --noconsole --clean --add-data "layout;layout" --add-data "..\api;api" --icon=layout\resources\logo.ico --collect-all "pyreadline3" --collect-all "sqlite3" --collect-all "Cryptodome" --collect-all "PIL" --name=3DS-RPC app.py
start dist
