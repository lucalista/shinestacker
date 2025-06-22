from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget, QLabel
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtCore import Qt, QMargins
from PySide6.QtGui import QPixmap
import webbrowser
import subprocess
import os
import platform


def open_file(file_path):
    try:
        if platform.system() == 'Darwin':       # macOS
            subprocess.call(('open', file_path))
        elif platform.system() == 'Windows':    # Windows
            os.startfile(file_path)
        else:                                   # linux variants
            subprocess.call(('xdg-open', file_path))
    except Exception:
        webbrowser.open("file://" + file_path)


class GuiPdfView(QPdfView):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setPageSpacing(0)
        self.setDocumentMargins(QMargins(0, 0, 0, 0))
        self.pdf_document = QPdfDocument()
        err = self.pdf_document.load(file_path)
        if err == QPdfDocument.Error.None_:
            self.setDocument(self.pdf_document)
            first_page_size = self.pdf_document.pagePointSize(0)
            zoom_factor = 0.35
            self.setZoomFactor(zoom_factor)
            self.setFixedSize(int(first_page_size.width() * zoom_factor) + 1,
                              int(first_page_size.height() * zoom_factor) + 1)
        else:
            raise RuntimeError(f"Can't load file: {file_path}. Error code: {err}.")

    def sizeHint(self):
        return self.size()

    def mouseReleaseEvent(self, event):
        open_file(self.file_path)


class GuiImageView(QWidget):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setFixedWidth(250)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.image_label)
        self.setLayout(self.layout)
        pixmap = QPixmap(file_path)
        if pixmap:
            scaled_pixmap = pixmap.scaledToWidth(250, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
        else:
            raise RuntimeError(f"Can't load file: {file_path}.")

    def sizeHint(self):
        return self.size()

    def mouseReleaseEvent(self, event):
        open_file(self.file_path)
