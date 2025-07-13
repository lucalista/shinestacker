#
# Install in a single file (slower startup):
#
# pyinstaller --onefile --name=focusstack-main --add-data="src/focusstack:focusstack" --hidden-import="focusstack.app.main" src/focusstack/app/main.py

#
# Install ina single directory
#
pyinstaller --onedir --name=focusstack-main --paths=src --collect-all=focusstack src/focusstack/app/main.py
cp -r ico dist/focusstack-main
