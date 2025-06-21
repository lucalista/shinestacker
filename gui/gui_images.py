from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
import sys
import webbrowser
import subprocess
import os
import platform

class MyPdfView(QPdfView):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path

    def mouseReleaseEvent(self, event):
        try:
            if platform.system() == 'Darwin':       # macOS
                subprocess.call(('open', file_path))
            elif platform.system() == 'Windows':    # Windows
                os.startfile(filepath)
            else:                                   # linux variants
                subprocess.call(('xdg-open', file_path))
        except Exception:
            webbrowser.open("file://" + self.file_path)


def new_pdf_view(file_path, parent=None):
    document = QPdfDocument()
    document.load(file_path)
    view = MyPdfView(file_path, parent)
    view.setDocument(document)
    view.setZoomFactor(0.25)
    view.show()
    return document, view
