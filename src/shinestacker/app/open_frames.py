# pylint: disable=C0114, C0116, E0611
import os
import sys
from PySide6.QtCore import QTimer


def open_files(editor, filenames):
    if len(filenames) == 1:
        QTimer.singleShot(100, lambda: editor.io_gui_handler.open_file(filenames[0]))
    else:
        def check_thread():
            thread = editor.io_gui_handler.loader_thread
            if thread is None or thread.isRunning():
                QTimer.singleShot(100, check_thread)
            else:
                editor.io_gui_handler.import_frames_from_files(filenames[1:])

        QTimer.singleShot(100, lambda: (
            editor.io_gui_handler.open_file(filenames[0]),
            QTimer.singleShot(100, check_thread)
        ))


def open_frames(editor, filename, path_list):
    if filename:
        filenames = filename.split(';')
        open_files(editor, filenames)
    elif path_list:
        reverse = False
        paths = path_list.split(';')
        filenames = []
        for path in paths:
            if os.path.exists(path) and os.path.isdir(path):
                all_entries = os.listdir(path)
                files = sorted([f for f in all_entries if os.path.isfile(os.path.join(path, f))],
                               reverse=reverse)
                full_paths = [os.path.join(path, f) for f in files]
                filenames += full_paths
            else:
                print(f"path {path} is invalid", file=sys.stderr)
                sys.exit(1)
        open_files(editor, filenames)
