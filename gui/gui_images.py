from PySide6.QtWidgets import QSizePolicy
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtCore import Qt, QSize
import sys
import webbrowser
import subprocess
import os
import platform


class MyPdfView(QPdfView):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)        
        self.setContentsMargins(0, 0, 0, 0)
        self.pdf_document = QPdfDocument()
        err = self.pdf_document.load(file_path)
        if err == QPdfDocument.Error.None_:
            self.setDocument(self.pdf_document)
            first_page_size = self.pdf_document.pagePointSize(0)
            zoom_factor = 0.3
            self.setZoomFactor(zoom_factor)
            self.setFixedSize(int(first_page_size.width() * zoom_factor) + 12,
                              int(first_page_size.height() * zoom_factor) + 16)
        else:
            raise RuntimeError(f"Can't load file: {file_path}. Error code: {err}.")
        
    def sizeHint(self):
        return self.size()

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

