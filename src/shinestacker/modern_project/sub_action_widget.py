# pylint: disable=E0611, R0903
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from .base_widget import ImgBaseWidget


class SubActionWidget(ImgBaseWidget):
    MAX_SCROLL_HEIGHT = 200

    def __init__(self, data_object, dark_theme=False, parent=None, horizontal_images=True):
        super().__init__(data_object, 35, dark_theme, False, 0, parent,
                         horizontal_images=horizontal_images)
        self.image_scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.image_scroll_area.setMaximumHeight(self.MAX_SCROLL_HEIGHT)
        self.progress_container = QWidget()
        self.progress_layout = QVBoxLayout(self.progress_container)
        self.progress_layout.setContentsMargins(0, 0, 0, 0)
        self.progress_layout.setSpacing(2)
        self.progress_layout.addWidget(self.image_scroll_area)
        self.main_layout.addWidget(self.progress_container)

    def widget_type(self):
        return 'SubActionWidget'

    def _adjust_vertical_area(self, tag):
        super()._adjust_vertical_area(tag)
        if hasattr(self, 'image_area_widget') and self.image_area_widget:
            current_height = self.image_area_widget.height()
            self.image_scroll_area.setMinimumHeight(min(current_height, self.MAX_SCROLL_HEIGHT))
