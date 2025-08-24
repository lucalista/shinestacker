# pylint: disable=C0114, C0115, C0116, E0611
import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel, QStackedWidget
from .. core.core_utils import get_app_base_path


class TabWidgetWithPlaceholder(QWidget):
    currentChanged = Signal(int)
    tabCloseRequested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.stacked_widget = QStackedWidget()
        self.layout.addWidget(self.stacked_widget)
        self.tab_widget = QTabWidget()
        self.stacked_widget.addWidget(self.tab_widget)
        self.placeholder = QLabel()
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rel_path = 'ico/focus_stack_bkg.png'
        icon_path = f'{get_app_base_path()}/{rel_path}'
        if not os.path.exists(icon_path):
            icon_path = f'{get_app_base_path()}/../{rel_path}'
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            pixmap = pixmap.scaled(250, 250, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            self.placeholder.setPixmap(pixmap)
        else:
            self.placeholder.setText("Run logs will appear here.")
        self.stacked_widget.addWidget(self.placeholder)
        self.tab_widget.currentChanged.connect(self._on_current_changed)
        self.tab_widget.tabCloseRequested.connect(self._on_tab_close_requested)
        self.update_placeholder_visibility()

    def _on_current_changed(self, index):
        self.currentChanged.emit(index)
        self.update_placeholder_visibility()

    def _on_tab_close_requested(self, index):
        self.tabCloseRequested.emit(index)
        self.update_placeholder_visibility()

    def update_placeholder_visibility(self):
        if self.tab_widget.count() == 0:
            self.stacked_widget.setCurrentIndex(1)
        else:
            self.stacked_widget.setCurrentIndex(0)

    # pylint: disable=C0103
    def addTab(self, widget, label):
        result = self.tab_widget.addTab(widget, label)
        self.update_placeholder_visibility()
        return result

    def removeTab(self, index):
        result = self.tab_widget.removeTab(index)
        self.update_placeholder_visibility()
        return result

    def count(self):
        return self.tab_widget.count()

    def setCurrentIndex(self, index):
        return self.tab_widget.setCurrentIndex(index)

    def currentIndex(self):
        return self.tab_widget.currentIndex()

    def currentWidget(self):
        return self.tab_widget.currentWidget()

    def widget(self, index):
        return self.tab_widget.widget(index)

    def indexOf(self, widget):
        return self.tab_widget.indexOf(widget)
    # pylint: enable=C0103
