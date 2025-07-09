pyinstaller --onefile --name=focusstack-main --add-data="src/focusstack:focusstack" --hidden-import="focusstack.app.main" src/focusstack/app/main.py
