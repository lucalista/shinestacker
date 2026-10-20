# pylint: disable=C0114, C0115, C0116, E0611, W0718, E1101, C0103, R0914, R0915
import traceback
import webbrowser
import subprocess
import os
import numpy as np
import cv2
from PySide6.QtWidgets import (
    QSizePolicy, QVBoxLayout, QWidget, QLabel, QStackedWidget, QMessageBox, QApplication)
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtCore import Qt, QMargins
from PySide6.QtGui import QPixmap, QImage
from .. config.gui_constants import gui_constants
from .. core.core_utils import running_under_windows, running_under_macos
from .. algorithms.utils import read_img


def open_file(file_path, parent_widget=None):
    if not os.path.exists(file_path):
        if parent_widget is None:
            app = QApplication.instance()
            if app:
                parent_widget = app.activeWindow()
        QMessageBox.warning(
            parent_widget,
            "File Not Found",
            f"The file could not be found:\n{file_path}",
            QMessageBox.StandardButton.Ok
        )
        return
    try:
        if running_under_macos():
            subprocess.call(('open', file_path))
        elif running_under_windows():
            os.startfile(file_path)
        else:
            subprocess.call(('xdg-open', file_path))
    except Exception:
        webbrowser.open("file://" + file_path)


class GuiPdfView(QPdfView):
    def __init__(self, file_path, parent=None, fixed_height=False):
        super().__init__(parent)
        self.file_path = file_path
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setPageSpacing(0)
        self.setDocumentMargins(QMargins(0, 0, 0, 0))
        self.setFocusPolicy(Qt.NoFocus)
        self.pdf_document = QPdfDocument()
        err = self.pdf_document.load(file_path)
        if err == QPdfDocument.Error.None_:
            self.setDocument(self.pdf_document)
            first_page_size = self.pdf_document.pagePointSize(0)
            extra_zoom = 0.75 if running_under_windows() else 1.0
            if fixed_height:
                zoom_factor = gui_constants.GUI_IMG_HEIGHT / first_page_size.height()
                width = int(first_page_size.width() * zoom_factor)
                self.setFixedSize(width, gui_constants.GUI_IMG_HEIGHT)
            else:
                zoom_factor = gui_constants.GUI_IMG_WIDTH / first_page_size.width()
                height = int(first_page_size.height() * zoom_factor)
                self.setFixedSize(gui_constants.GUI_IMG_WIDTH, height)
            self.setZoomFactor(zoom_factor * extra_zoom)
        else:
            raise RuntimeError(f"Can't load file: {file_path}. Error code: {err}.")
        self.setStyleSheet('''
        QWidget {
            border: 2px solid #0000a0;
        }
        QWidget:hover {
            border: 2px solid #a0a0ff;
        }
        ''')

    def sizeHint(self):
        return self.size()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            open_file(self.file_path, self.parent())
            return
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event):
        event.ignore()


class GuiImageView(QWidget):
    def __init__(self, file_path, parent=None, fixed_height=False):
        super().__init__(parent)
        self.file_path = file_path
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.image_label)
        self.setFocusPolicy(Qt.NoFocus)
        self.setLayout(self.main_layout)
        try:
            img = read_img(file_path)
            if img is None:
                raise RuntimeError(f"Failed to load image: {file_path}")
            if img.dtype == np.uint16:
                img = (img // 256).astype(np.uint8)
            height, width = img.shape[:2]
            if fixed_height:
                scale_factor = gui_constants.GUI_IMG_HEIGHT / height
                new_width = int(width * scale_factor)
                target_width = new_width
                target_height = gui_constants.GUI_IMG_HEIGHT
            else:
                scale_factor = gui_constants.GUI_IMG_WIDTH / width
                new_height = int(height * scale_factor)
                target_width = gui_constants.GUI_IMG_WIDTH
                target_height = new_height

            def resize_high_quality(image, target_width, target_height):
                return cv2.resize(image, (target_width, target_height),
                                  interpolation=cv2.INTER_LANCZOS4)

            img = resize_high_quality(img, target_width, target_height)
            if len(img.shape) == 3:
                h, w, ch = img.shape
                if ch == 4:
                    rgb_image = cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA)
                    bytes_per_line = ch * w
                    q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGBA8888)
                elif ch == 3:
                    rgb_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    bytes_per_line = 3 * w
                    q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                else:
                    raise RuntimeError(f"Unsupported number of channels: {ch}")
            else:
                h, w = img.shape
                bytes_per_line = w
                q_img = QImage(img.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
            pixmap = QPixmap.fromImage(q_img)
            if pixmap.isNull():
                raise RuntimeError(f"Failed to create pixmap from image: {file_path}")
            self.image_label.setPixmap(pixmap)
            self.setFixedSize(pixmap.size())
        except Exception as e:
            traceback.print_exc()
            raise RuntimeError(f"Can't load file: {file_path}. Error: {str(e)}") from e
        self.setStyleSheet('''
        QWidget {
            border: 2px solid #0000a0;
        }
        QWidget:hover {
            border: 2px solid #d8d8ff;
        }
        ''')

    def sizeHint(self):
        return self.size()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            open_file(self.file_path, self.parent())
            return
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event):
        event.ignore()


class GuiOpenApp(QWidget):
    def __init__(self, file_path, parent=None, fixed_height=False):
        super().__init__(parent)
        self.file_path = file_path
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.image_label)
        self.setFocusPolicy(Qt.NoFocus)
        self.setLayout(self.main_layout)
        pixmap = QPixmap(file_path)
        if pixmap:
            if fixed_height:
                scaled_pixmap = pixmap.scaledToHeight(
                    gui_constants.GUI_IMG_HEIGHT, Qt.SmoothTransformation)
                self.setFixedSize(scaled_pixmap.size())
            else:
                scaled_pixmap = pixmap.scaledToWidth(
                    gui_constants.GUI_IMG_WIDTH, Qt.SmoothTransformation)
                self.setFixedSize(scaled_pixmap.size())
            self.image_label.setPixmap(scaled_pixmap)
        else:
            raise RuntimeError(f"Can't load file: {file_path}.")
        self.setStyleSheet('''
        QWidget {
            border: 2px solid #a00000;
        }
        QWidget:hover {
            border: 2px solid #ffd8d8;
        }
        ''')

    def sizeHint(self):
        return self.size()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            app = None
            stacked_widget = self.parent().window().findChild(QStackedWidget)
            if stacked_widget:
                for child in stacked_widget.children():
                    if child.metaObject().className() == 'MainWindow':
                        app = child
                        break
                else:
                    raise RuntimeError("MainWindow object not found")
            if app:
                app.retouch_callback(self.file_path)
            else:
                raise RuntimeError("MainWindow object not found")
            return
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event):
        event.ignore()
