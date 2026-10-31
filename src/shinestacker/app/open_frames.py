import os
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox, QApplication
from .. algorithms.utils import extension_supported_input


def open_files(editor, filenames):
    if len(filenames) == 1:
        QTimer.singleShot(100, lambda: editor.io_gui_handler.open_file(filenames[0]))
        return True

    def check_thread():
        thread = editor.io_gui_handler.loader_thread
        if thread is None or thread.isRunning():
            QTimer.singleShot(100, check_thread)
        else:
            editor.io_gui_handler.import_frames_from_files(filenames[1:])

    if len(filenames) > 0:
        QTimer.singleShot(100, lambda: (
            editor.io_gui_handler.open_file(filenames[0]),
            QTimer.singleShot(100, check_thread)
        ))
        return True
    app = QApplication.instance()
    if app:
        parent_widget = app.activeWindow()
        QMessageBox.warning(parent_widget, "File Not Found",
                            "Can't find processed images to retouch",
                            QMessageBox.StandardButton.Ok)
    return False


def open_frames(editor, filename, path_list):
    if filename:
        filenames = filename.split(';')
        return open_files(editor, filenames)
    reverse = False
    paths = path_list.split(';')
    filenames = []
    for path in paths:
        if os.path.exists(path) and os.path.isdir(path):
            all_entries = os.listdir(path)
            files = sorted([f for f in all_entries if os.path.isfile(os.path.join(path, f))],
                           reverse=reverse)
            full_paths = [os.path.join(path, f) for f in files if extension_supported_input(f)]
            filenames += full_paths
        else:
            app = QApplication.instance()
            if app:
                parent_widget = app.activeWindow()
                QMessageBox.warning(parent_widget, "File Not Found",
                                    "Can't find processed images",
                                    QMessageBox.StandardButton.Ok)
                return False
    return open_files(editor, filenames)
