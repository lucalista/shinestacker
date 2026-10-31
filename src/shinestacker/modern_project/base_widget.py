# pylint: disable=R0903, R0913, R0917, R0902, R0915, R0904
import os
from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout, QSizePolicy, QLayout, QScrollArea)
from ..config.constants import constants
from ..gui.gui_images import GuiPdfView, GuiOpenApp, GuiImageView
from ..gui.colors import ColorPalette
from ..gui.icon_manager import IconManager


CONDITIONAL_ICONS = {
    'pyramid_stack': {
        'key': 'stacker',
        'value': constants.STACK_ALGO_PYRAMID,
        'types_names': [
            constants.ACTION_FOCUSSTACK, constants.ACTION_FOCUSSTACKBUNCH],
        'default_for_types_names': [
            constants.ACTION_FOCUSSTACK, constants.ACTION_FOCUSSTACKBUNCH],
        'icon': 'pyramid-small-icon',
        'tooltip': 'Pyramid stack algorithm'
    },
    'depth_map': {
        'key': 'stacker',
        'value': constants.STACK_ALGO_DEPTH_MAP,
        'types_names': [
            constants.ACTION_FOCUSSTACK, constants.ACTION_FOCUSSTACKBUNCH],
        'default_for_types_names': [],
        'icon': 'depth-map-small-icon',
        'tooltip': 'Depth Map stack algorithm'
    },
}


def check_icon_condition(data_object, icon_config):
    if data_object.type_name not in icon_config.get('types_names', []):
        return False
    key = icon_config['key']
    expected_value = icon_config['value']
    if key in data_object.params:
        return data_object.params[key] == expected_value
    return data_object.type_name in icon_config.get('default_for_types_names', [])


class BaseWidget(QFrame, IconManager):
    clicked = Signal()
    double_clicked = Signal()
    enabled_toggled = Signal(bool)

    def __init__(self, data_object, min_height=40, dark_theme=False,
                 horizontal_layout=False, color_level=0, parent=None):
        QFrame.__init__(self, parent)
        IconManager.__init__(self, dark_theme)
        self.icon_size = 16
        self.data_object = data_object
        self._enabled = True
        self.horizontal_layout = horizontal_layout
        self.min_height = min_height
        self._color_level = color_level
        self.path_label = None
        self.child_widgets = []
        self.top_container = None
        self.top_layout = None
        self.icons_container = None
        self.icons_layout = None
        self.path_label_in_top_row = None
        self.child_container = None
        self.child_container_layout = None
        self.conditional_icons = {}
        self.conditional_icon_names = {}
        self.setFocusPolicy(Qt.NoFocus)
        self.setAttribute(Qt.WA_Hover, True)
        self.name_label = None
        self.enabled_icon = None
        self.path_label_in_top_row = True
        if self.data_object:
            widget_state = self.data_object.metadata.get('widget_state')
            if widget_state is not None:
                self._restore_widget_state(widget_state)
        self.image_layout = None
        self.image_area_widget = None
        self._init_widget(data_object)
        self._update_stylesheet()
        self.setCursor(Qt.ArrowCursor)
        self._create_conditional_icons()

    def _init_widget(self, data_object):
        self.setMinimumHeight(self.min_height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(5)
        self.main_layout.setSizeConstraint(QLayout.SetMinAndMaxSize)
        self.main_layout.setAlignment(Qt.AlignTop)
        self.top_container = QWidget()
        self.top_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.top_layout = QHBoxLayout(self.top_container)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.setSpacing(5)
        self.top_layout.setAlignment(Qt.AlignTop)
        self.name_label = QLabel()
        self.name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.name_label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Maximum)
        self.top_layout.addWidget(self.name_label)
        self.path_label = QLabel()
        self.path_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.path_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.top_layout.addWidget(self.path_label, 1)
        self.icons_container = QWidget()
        self.icons_container.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Maximum)
        self.icons_layout = QHBoxLayout(self.icons_container)
        self.icons_layout.setContentsMargins(0, 0, 0, 0)
        self.icons_layout.setSpacing(5)
        self.icons_layout.setAlignment(Qt.AlignTop)
        self.enabled_icon = QLabel()
        self.enabled_icon.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.enabled_icon.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.enabled_icon.mousePressEvent = self._on_enabled_icon_clicked
        self.icons_layout.addWidget(self.enabled_icon)
        self.top_layout.addWidget(self.icons_container)
        self.main_layout.addWidget(self.top_container)
        self.child_container = QWidget()
        self.child_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        if self.horizontal_layout:
            self.child_container_layout = QHBoxLayout()
        else:
            self.child_container_layout = QVBoxLayout()
        self.child_container_layout.setContentsMargins(0, 5, 0, 0)
        self.child_container_layout.setSpacing(5)
        self.child_container_layout.setAlignment(Qt.AlignTop)
        self.child_container.setLayout(self.child_container_layout)
        self.main_layout.addWidget(self.child_container)
        self.setLayout(self.main_layout)
        name = f"<b>{data_object.params['name']}</b> [{data_object.type_name}]"
        self.set_name(name)
        self._enabled = data_object.params.get('enabled', True)
        self._update_enabled_icon()

    def set_button_icon(self, button, icon_name):
        icon = self.get_icon(icon_name)
        button.setIcon(icon)
        button.setIconSize(QSize(self.icon_size, self.icon_size))

    def update_metadata(self):
        if self.data_object is None:
            return
        widget_state = self._capture_widget_state()
        if widget_state:
            self.data_object.metadata['widget_state'] = widget_state

    def _capture_widget_state(self):
        return {}

    def _restore_widget_state(self, state):
        pass

    def _create_conditional_icons(self):
        for icon_name, icon_data in CONDITIONAL_ICONS.items():
            if check_icon_condition(self.data_object, icon_data):
                self._add_conditional_icon(icon_name, icon_data['icon'], icon_data['tooltip'])

    def _add_conditional_icon(self, name, icon_name, tooltip):
        if name in self.conditional_icons:
            return
        label = QLabel()
        self.set_label_icon(label, icon_name)
        label.setToolTip(tooltip)
        self.icons_layout.insertWidget(len(self.conditional_icons), label)
        self.conditional_icons[name] = label
        self.conditional_icon_names[name] = icon_name

    def _remove_conditional_icons(self):
        for label in self.conditional_icons.values():
            self.icons_layout.removeWidget(label)
            label.deleteLater()
        self.conditional_icons.clear()
        self.conditional_icon_names.clear()

    def _update_conditional_icons(self):
        self._remove_conditional_icons()
        self._create_conditional_icons()

    def add_child_widget(self, child_widget, add_to_layout=True, can_update=True):
        self.child_widgets.append(child_widget)
        if add_to_layout:
            self.child_container_layout.addWidget(child_widget)
        if can_update:
            self.update_metadata()

    def set_horizontal_layout(self, horizontal):
        if self.horizontal_layout != horizontal:
            self.horizontal_layout = horizontal
            old_container = self.child_container
            self.child_container = QWidget()
            if horizontal:
                self.child_container_layout = QHBoxLayout()
            else:
                self.child_container_layout = QVBoxLayout()
            self.child_container_layout.setContentsMargins(0, 5, 0, 0)
            self.child_container_layout.setSpacing(5)
            for widget in self.child_widgets:
                self.child_container_layout.addWidget(widget)
            self.child_container.setLayout(self.child_container_layout)
            self.main_layout.replaceWidget(old_container, self.child_container)
            old_container.deleteLater()

    def _add_path_label(self, text):
        if self.path_label.text() == text:
            return
        self.path_label.setText(text)
        QTimer.singleShot(0, self._check_and_adjust_layout)

    def _check_and_adjust_layout(self):
        if not self.path_label.text():
            return
        available_width = self.top_container.width() - 20
        name_width = self.name_label.sizeHint().width()
        path_width = self.path_label.sizeHint().width()
        icons_width = self.icons_container.minimumSizeHint().width()
        total_needed = name_width + path_width + icons_width + 20
        if total_needed > available_width and self.path_label_in_top_row:
            self.top_layout.removeWidget(self.path_label)
            self.main_layout.insertWidget(1, self.path_label)
            self.path_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.path_label_in_top_row = False
            self.top_layout.setStretch(2, 0)
            self.icons_container.setMaximumWidth(icons_width)
        elif total_needed <= available_width and not self.path_label_in_top_row:
            self.main_layout.removeWidget(self.path_label)
            self.top_layout.insertWidget(1, self.path_label)
            self.path_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self.path_label_in_top_row = True
            self.top_layout.setStretch(1, 1)
            self.top_layout.setStretch(2, 0)
            self.icons_container.setMaximumWidth(icons_width)

    def _on_enabled_icon_clicked(self, event):
        self._enabled = not self._enabled
        self._update_enabled_icon()
        self._update_stylesheet()
        self.clicked.emit()
        self.enabled_toggled.emit(self._enabled)
        event.accept()

    def widget_type(self):
        return ''

    def _format_path(self, path):
        if os.path.isabs(path):
            return ".../" + os.path.basename(path)
        return path

    def _update_stylesheet(self):
        if self.dark_theme:
            border_color = ColorPalette.LIGHT_BLUE.hex()
            selected_bg = ColorPalette.DARK_BLUE.hex()
            disabled_border_color = ColorPalette.LIGHT_RED.hex()
            disabled_selected_bg = ColorPalette.DARK_RED.hex()
        else:
            border_color = ColorPalette.DARK_BLUE.hex()
            selected_bg = ColorPalette.LIGHT_BLUE.hex()
            disabled_border_color = ColorPalette.DARK_RED.hex()
            disabled_selected_bg = ColorPalette.LIGHT_RED.hex()
        widget_type = self.widget_type()
        if self._enabled:
            border = border_color
            selected = selected_bg
        else:
            border = disabled_border_color
            selected = disabled_selected_bg
        hover_color = self._get_hover_color()
        stylesheet = f"""
            {widget_type} {{
                border: 2px solid #{border};
                border-radius: 4px;
                margin: 2px;
                background-color: palette(window);
            }}
            {widget_type}[hovered="true"] {{
                background-color: #{hover_color};
            }}
            {widget_type}[selected="true"] {{
                background-color: #{selected};
            }}
            {widget_type}[selected="true"][hovered="true"] {{
                background-color: #{selected};
            }}
        """
        self.setStyleSheet(stylesheet)
        self.style().unpolish(self)
        self.style().polish(self)

    def _get_hover_color(self):
        if not self._enabled:
            if self.dark_theme:
                colors = [ColorPalette.DARK_RED_0, ColorPalette.DARK_RED_1,
                          ColorPalette.DARK_RED_2]
            else:
                colors = [ColorPalette.LIGHT_RED_0, ColorPalette.LIGHT_RED_1,
                          ColorPalette.LIGHT_RED_2]
        else:
            if self.dark_theme:
                colors = [ColorPalette.DARK_BLUE_0, ColorPalette.DARK_BLUE_1,
                          ColorPalette.DARK_BLUE_2]
            else:
                colors = [ColorPalette.LIGHT_BLUE_0, ColorPalette.LIGHT_BLUE_1,
                          ColorPalette.LIGHT_BLUE_2]
        return colors[self._color_level].hex()

    def set_label_icon(self, label, icon_name):
        pixmap = self.get_icon(icon_name).pixmap(self.icon_size, self.icon_size)
        label.setPixmap(pixmap)
        label.setFixedSize(QSize(self.icon_size, self.icon_size))

    def _update_icons(self):
        self._update_enabled_icon()
        for name, label in self.conditional_icons.items():
            icon_name = self.conditional_icon_names.get(name)
            if icon_name:
                self.set_label_icon(label, icon_name)
        self._check_and_adjust_layout()

    def _update_enabled_icon(self):
        icon_name = "enabled-small-icon" if self._enabled else "disabled-small-icon"
        self.set_label_icon(self.enabled_icon, icon_name)
        self.enabled_icon.setToolTip("Disable" if self._enabled else "Enable")

    def clear_all(self):
        for child in self.child_widgets:
            child.clear_all()

    # pylint: disable=C0103
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.path_label and self.path_label.text():
            self._check_and_adjust_layout()

    def mousePressEvent(self, event):
        self.clicked.emit()
        event.accept()

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()
        event.accept()

    def contextMenuEvent(self, event):
        widget = self
        while widget:
            if type(widget).__name__ == 'ModernProjectView':
                widget.contextMenuEvent(event)
                break
            widget = widget.parent()
        event.accept()

    def enterEvent(self, event):
        super().enterEvent(event)
        self.setProperty("hovered", "true")
        self.style().unpolish(self)
        self.style().polish(self)
        self.setCursor(Qt.PointingHandCursor)
        event.accept()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.setProperty("hovered", "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.setCursor(Qt.ArrowCursor)
        event.accept()
    # pylint: enable=C0103

    def set_selected(self, selected):
        self.setProperty("selected", "true" if selected else "false")
        self._update_stylesheet()

    def set_dark_theme(self, dark_theme):
        super().set_dark_theme(dark_theme)
        self.setProperty("dark_theme", dark_theme)
        self._update_stylesheet()
        for child in self.child_widgets:
            child.set_dark_theme(dark_theme)

    def set_name(self, name):
        self.name_label.setText(name)

    def update_enabled(self, data_object=None):
        if data_object is None:
            data_object = self.data_object
        self._enabled = data_object.enabled()
        self._update_enabled_icon()

    def update(self, data_object=None):
        if data_object is None:
            data_object = self.data_object
        else:
            self.data_object = data_object
        name = f"<b>{data_object.params['name']}</b> [{data_object.type_name}]"
        self.set_name(name)
        self.update_enabled(data_object)
        self._update_conditional_icons()
        self._update_icons()
        self._update_stylesheet()
        self.update_path_recursive()

    def update_recursive(self):
        self.update()
        for child in self.child_widgets:
            child.update_recursive()

    def update_path_recursive(self):
        self.update_path_label()
        for child in self.child_widgets:
            child.update_path_recursive()

    def update_path_label(self):
        pass

    def scroll_area_css(self, orientation):
        size = 'height' if orientation == 'vertical' else 'width'
        return f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background: transparent;
            }}
            QScrollBar:{orientation} {{
                height: 6px;
                border: none;
                background: transparent;
            }}
            QScrollBar::handle:{orientation} {{
                background: #808080;
                border-radius: 3px;
                min-{size}: 25px;
            }}
            QScrollBar::handle:{orientation}:hover {{
                background: #404040;
            }}
            QScrollBar::add-line:{orientation}, QScrollBar::sub-line:{orientation} {{
                width: 0px;
                height: 0px;
            }}
        """

    def capture_widget_state(self):
        state = {
            'children': [child.capture_widget_state() for child in self.child_widgets]
        }
        return state

    def restore_widget_state(self, state):
        if not state:
            return
        if 'children' in state:
            for i, child_state in enumerate(state['children']):
                if i < len(self.child_widgets):
                    self.child_widgets[i].restore_widget_state(child_state)

    def clear_metadata(self):
        pass

    def refresh_from_metadata(self):
        self.update()


class ImgBaseWidget(BaseWidget):
    def __init__(self, data_object, min_height=40, dark_theme=False,
                 horizontal_layout=False, color_level=0, parent=None, horizontal_images=False):
        self._pending_image_views_state = None
        self.image_views_by_tag = {}
        self.scroll_areas_by_tag = {}
        self.image_layouts_by_tag = {}
        self.image_area_widgets_by_tag = {}
        super().__init__(
            data_object, min_height, dark_theme, horizontal_layout, color_level, parent)
        self.horizontal_images = horizontal_images
        self.scroll_areas_container = QWidget()
        self.scroll_areas_container_layout = QVBoxLayout(self.scroll_areas_container)
        self.scroll_areas_container_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_areas_container_layout.setSpacing(5)
        self.scroll_areas_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.child_container_layout.addWidget(self.scroll_areas_container)
        self._create_scroll_area_for_tag("_default")
        self.image_views = self.image_views_by_tag["_default"]
        self.image_scroll_area = self.scroll_areas_by_tag["_default"]
        self.image_layout = self.image_layouts_by_tag["_default"]
        self.image_area_widget = self.image_area_widgets_by_tag["_default"]
        if self._pending_image_views_state is not None:
            self._process_pending_image_views()
        if self._pending_image_views_state is not None:
            self._process_pending_image_views()
            QTimer.singleShot(100, self._delayed_size_adjustment)

    def _delayed_size_adjustment(self):
        for tag, val in self.image_views_by_tag.items():
            if val:
                self._adjust_image_area(tag)
                if tag in self.image_area_widgets_by_tag:
                    self.image_area_widgets_by_tag[tag].adjustSize()

    def _get_sorted_tags(self):
        tags = list(self.scroll_areas_by_tag.keys())
        return sorted(tags, key=lambda x: (x != "_default", x))

    def _apply_scroll_area_style(self, scroll_area, horizontal):
        if horizontal:
            scroll_area.setStyleSheet(self.scroll_area_css('horizontal'))
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        else:
            scroll_area.setStyleSheet(self.scroll_area_css('vertical'))
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def _create_scroll_area_for_tag(self, tag):
        if tag in self.scroll_areas_by_tag:
            return
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._apply_scroll_area_style(scroll_area, self.horizontal_images)
        if self.horizontal_images:
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
        else:
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            layout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
        area_widget = QWidget()
        layout.setSpacing(5)
        layout.setAlignment(Qt.AlignTop)
        area_widget.setLayout(layout)
        scroll_area.setWidget(area_widget)
        scroll_area.setVisible(False)
        self.scroll_areas_by_tag[tag] = scroll_area
        self.image_layouts_by_tag[tag] = layout
        self.image_area_widgets_by_tag[tag] = area_widget
        self.image_views_by_tag[tag] = []
        self._reorder_scroll_areas()

    def _reorder_scroll_areas(self):
        for scroll_area in self.scroll_areas_by_tag.values():
            self.scroll_areas_container_layout.removeWidget(scroll_area)
        for tag in self._get_sorted_tags():
            self.scroll_areas_container_layout.addWidget(self.scroll_areas_by_tag[tag])

    def _process_pending_image_views(self):
        if self._pending_image_views_state is not None:
            for tag, views_state in self._pending_image_views_state.items():
                for view_state in views_state:
                    file_path = view_state.get('file_path')
                    view_type = view_state.get('type', 'GuiImageView')
                    if file_path and os.path.exists(file_path):
                        if view_type == 'GuiPdfView':
                            image_view = GuiPdfView(file_path, self)
                        elif view_type == 'GuiOpenApp':
                            image_view = GuiOpenApp(file_path, self)
                        else:
                            image_view = GuiImageView(file_path, self)
                        if tag not in self.scroll_areas_by_tag:
                            self._create_scroll_area_for_tag(tag)
                        self.image_views_by_tag[tag].append(image_view)
                        self.image_layouts_by_tag[tag].addWidget(image_view)
                        self.scroll_areas_by_tag[tag].setVisible(True)
                        self._adjust_image_area(tag)
            self._pending_image_views_state = None

    def set_image_orientation(self, horizontal):
        if self.horizontal_images == horizontal:
            return
        self.horizontal_images = horizontal
        for tag, scroll_area in self.scroll_areas_by_tag.items():
            self._apply_scroll_area_style(scroll_area, horizontal)
            current_views = list(scroll_area)
            self.image_views_by_tag[tag].clear()
            area_widget = QWidget()
            if horizontal:
                layout = QHBoxLayout()
                layout.setContentsMargins(0, 0, 0, 0)
            else:
                layout = QVBoxLayout()
                layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(5)
            layout.setAlignment(Qt.AlignTop)
            for view in current_views:
                self.image_views_by_tag[tag].append(view)
                layout.addWidget(view)
            area_widget.setLayout(layout)
            self.image_layouts_by_tag[tag] = layout
            self.image_area_widgets_by_tag[tag] = area_widget
            scroll_area.setWidget(area_widget)
            if tag == "_default":
                self.image_area_widget = area_widget
                self.image_layout = layout
                self.image_views = self.image_views_by_tag["_default"]
            if current_views:
                scroll_area.setVisible(True)
                self._adjust_image_area(tag)
            else:
                scroll_area.setVisible(False)
                scroll_area.setMinimumHeight(0)
        if "_default" in self.scroll_areas_by_tag:
            self.image_scroll_area = self.scroll_areas_by_tag["_default"]

    def clear_all(self):
        self.clear_images()
        super().clear_all()

    def clear_images(self, tag=None):
        if tag is not None:
            if tag in self.image_views_by_tag:
                for view in self.image_views_by_tag[tag]:
                    if tag in self.image_layouts_by_tag:
                        self.image_layouts_by_tag[tag].removeWidget(view)
                    view.deleteLater()
                self.image_views_by_tag[tag].clear()
                self.scroll_areas_by_tag[tag].setVisible(False)
                self.scroll_areas_by_tag[tag].setMinimumHeight(0)
        else:
            for tag_key in list(self.image_views_by_tag.keys()):
                for view in self.image_views_by_tag[tag_key]:
                    if tag_key in self.image_layouts_by_tag:
                        self.image_layouts_by_tag[tag_key].removeWidget(view)
                    view.deleteLater()
                self.image_views_by_tag[tag_key].clear()
                self.scroll_areas_by_tag[tag_key].setVisible(False)
                self.scroll_areas_by_tag[tag_key].setMinimumHeight(0)
        self.update_metadata()

    def add_image_view(self, image_view, tag="_default", can_update=True):
        if tag not in self.scroll_areas_by_tag:
            self._create_scroll_area_for_tag(tag)
        self.image_views_by_tag[tag].append(image_view)
        self.image_layouts_by_tag[tag].addWidget(image_view)
        self.scroll_areas_by_tag[tag].setVisible(True)
        self._adjust_image_area(tag)
        QTimer.singleShot(0, self.image_area_widgets_by_tag[tag].adjustSize)
        if tag == "_default":
            self.image_views = self.image_views_by_tag["_default"]
        if can_update:
            self.update_metadata()

    def _adjust_image_area(self, tag):
        if tag not in self.image_views_by_tag or not self.image_views_by_tag[tag]:
            return
        if self.horizontal_images:
            self._adjust_horizontal_area(tag)
        else:
            self._adjust_vertical_area(tag)

    def _adjust_horizontal_area(self, tag):
        views = self.image_views_by_tag[tag]
        layout = self.image_layouts_by_tag[tag]
        area_widget = self.image_area_widgets_by_tag[tag]
        scroll_area = self.scroll_areas_by_tag[tag]
        max_height = max(view.sizeHint().height() for view in views)
        total_width = sum(view.sizeHint().width() for view in views)
        total_width += layout.spacing() * (len(views) - 1)
        extra_scrollbar_space = 6
        area_widget.setFixedWidth(total_width)
        area_widget.setFixedHeight(max_height + extra_scrollbar_space)
        scrollbar = scroll_area.horizontalScrollBar()
        scrollbar_height = scrollbar.sizeHint().height() if scrollbar.maximum() > 0 else 0
        scroll_area.setMinimumHeight(max_height + scrollbar_height + extra_scrollbar_space + 6)

    def _adjust_vertical_area(self, tag):
        views = self.image_views_by_tag[tag]
        layout = self.image_layouts_by_tag[tag]
        area_widget = self.image_area_widgets_by_tag[tag]
        scroll_area = self.scroll_areas_by_tag[tag]
        total_height = sum(view.sizeHint().height() for view in views)
        total_height += layout.spacing() * (len(views) - 1)
        total_height += 10
        max_width = max(view.sizeHint().width() for view in views)
        area_widget.setFixedHeight(total_height)
        area_widget.setFixedWidth(max_width)
        scroll_area.setMinimumHeight(min(total_height, 200))

    def _capture_widget_state(self):
        state = super()._capture_widget_state()
        image_views_state_by_tag = {}
        for tag, views in self.image_views_by_tag.items():
            tag_views_state = []
            for view in views:
                if hasattr(view, 'file_path'):
                    view_state = {'file_path': view.file_path, 'type': type(view).__name__}
                    if hasattr(view, 'app'):
                        view_state['app'] = view.app
                    tag_views_state.append(view_state)
            if tag_views_state:
                image_views_state_by_tag[tag] = tag_views_state
        state['image_views_by_tag'] = image_views_state_by_tag
        return state

    def _restore_widget_state(self, state):
        super()._restore_widget_state(state)
        if 'image_views_by_tag' in state:
            self._pending_image_views_state = state['image_views_by_tag']
        elif 'image_views' in state:
            self._pending_image_views_state = {"_default": state['image_views']}

    def clear_metadata(self):
        self.clear_images()

    def refresh_from_metadata(self):
        widget_state = None
        if self.data_object is not None:
            widget_state = self.data_object.metadata.get('widget_state')
        for tag in list(self.image_views_by_tag.keys()):
            for view in self.image_views_by_tag[tag]:
                if tag in self.image_layouts_by_tag:
                    self.image_layouts_by_tag[tag].removeWidget(view)
                view.deleteLater()
            self.image_views_by_tag[tag].clear()
            self.scroll_areas_by_tag[tag].setVisible(False)
            self.scroll_areas_by_tag[tag].setMinimumHeight(0)
        if widget_state:
            self._restore_widget_state(widget_state)
            self._process_pending_image_views()
        self.update_metadata()
        super().refresh_from_metadata()
