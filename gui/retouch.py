import sys
sys.path.append('../')
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QTimer
from gui.gui_utils import disable_macos_special_menu_items
from gui.image_editor_ui import ImageEditorUI, DONT_USE_NATIVE_MENU

if __name__ == "__main__":
    app = QApplication(sys.argv)
    if DONT_USE_NATIVE_MENU:
        app.setAttribute(Qt.AA_DontUseNativeMenuBar)
    else:
        disable_macos_special_menu_items()
    app.setWindowIcon(QIcon('ico/focus_stack.png'))
    file_to_open = None
    if len(sys.argv) > 1:
        file_to_open = sys.argv[1]
    editor = ImageEditorUI()
    editor.show()
    if file_to_open:
        QTimer.singleShot(100, lambda: editor.open_file(file_to_open))
    sys.exit(app.exec())
