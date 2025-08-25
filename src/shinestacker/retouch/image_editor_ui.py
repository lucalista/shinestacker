# pylint: disable=C0114, C0115, C0116, E0611, R0902, R0914, R0915, R0904
import numpy as np
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
                               QListWidget, QSlider, QMainWindow, QMessageBox)
from PySide6.QtGui import QShortcut, QKeySequence, QAction, QActionGroup
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from .. config.constants import constants
from .. config.gui_constants import gui_constants
from .image_viewer import ImageViewer
from .shortcuts_help import ShortcutsHelp
from .brush import Brush
from .brush_tool import BrushTool
from .layer_collection import LayerCollectionHandler
from .undo_manager import UndoManager
from .layer_collection import LayerCollection
from .io_gui_handler import IOGuiHandler
from .display_manager import DisplayManager
from .filter_manager import FilterManager
from .denoise_filter import DenoiseFilter
from .unsharp_mask_filter import UnsharpMaskFilter
from .white_balance_filter import WhiteBalanceFilter
from .vignetting_filter import VignettingFilter


class ImageEditorUI(QMainWindow, LayerCollectionHandler):
    def __init__(self):
        QMainWindow.__init__(self)
        LayerCollectionHandler.__init__(self, LayerCollection())
        self.thumbnail_highlight = gui_constants.THUMB_MASTER_HI_COLOR
        self.undo_manager = UndoManager()
        self.undo_action = None
        self.redo_action = None
        self.undo_manager.stack_changed.connect(self.update_undo_redo_actions)
        self.io_gui_handler = None
        self.display_manager = None
        self.brush = Brush()
        self.brush_tool = BrushTool()
        self.modified = False
        self.mask_layer = None
        self.filter_manager = FilterManager(self)
        self.filter_manager.register_filter("Denoise", DenoiseFilter)
        self.filter_manager.register_filter("Unsharp Mask", UnsharpMaskFilter)
        self.filter_manager.register_filter("White Balance", WhiteBalanceFilter)
        self.filter_manager.register_filter("Vignetting Correction", VignettingFilter)
        self.shortcuts_help_dialog = None

        self.update_title()
        self.resize(1400, 900)
        center = QGuiApplication.primaryScreen().geometry().center()
        self.move(center - self.rect().center())
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        self.image_viewer = ImageViewer(self.layer_collection)
        self.image_viewer.temp_view_requested.connect(self.handle_temp_view)
        self.image_viewer.brush_operation_started.connect(self.begin_copy_brush_area)
        self.image_viewer.brush_operation_continued.connect(self.continue_copy_brush_area)
        self.image_viewer.brush_operation_ended.connect(self.end_copy_brush_area)
        self.image_viewer.brush_size_change_requested.connect(self.handle_brush_size_change)
        self.image_viewer.setFocusPolicy(Qt.StrongFocus)
        side_panel = QWidget()
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(2)

        brush_panel = QFrame()
        brush_panel.setFrameShape(QFrame.StyledPanel)
        brush_panel.setContentsMargins(0, 0, 0, 0)
        brush_layout = QVBoxLayout(brush_panel)
        brush_layout.setContentsMargins(0, 0, 0, 0)
        brush_layout.setSpacing(2)

        brush_label = QLabel("Brush Size")
        brush_label.setAlignment(Qt.AlignCenter)
        brush_layout.addWidget(brush_label)

        self.brush_size_slider = QSlider(Qt.Horizontal)
        self.brush_size_slider.setRange(0, gui_constants.BRUSH_SIZE_SLIDER_MAX)

        def brush_size_to_slider(size):
            if size <= gui_constants.BRUSH_SIZES['min']:
                return 0
            if size >= gui_constants.BRUSH_SIZES['max']:
                return gui_constants.BRUSH_SIZE_SLIDER_MAX
            normalized = ((size - gui_constants.BRUSH_SIZES['min']) /
                          gui_constants.BRUSH_SIZES['max']) ** (1 / gui_constants.BRUSH_GAMMA)
            return int(normalized * gui_constants.BRUSH_SIZE_SLIDER_MAX)

        self.brush_size_slider.setValue(brush_size_to_slider(self.brush.size))
        brush_layout.addWidget(self.brush_size_slider)

        hardness_label = QLabel("Brush Hardness")
        hardness_label.setAlignment(Qt.AlignCenter)
        brush_layout.addWidget(hardness_label)
        self.hardness_slider = QSlider(Qt.Horizontal)
        self.hardness_slider.setRange(0, 100)
        self.hardness_slider.setValue(self.brush.hardness)
        brush_layout.addWidget(self.hardness_slider)

        opacity_label = QLabel("Brush Opacity")
        opacity_label.setAlignment(Qt.AlignCenter)
        brush_layout.addWidget(opacity_label)
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(self.brush.opacity)
        brush_layout.addWidget(self.opacity_slider)

        flow_label = QLabel("Brush Flow")
        flow_label.setAlignment(Qt.AlignCenter)
        brush_layout.addWidget(flow_label)
        self.flow_slider = QSlider(Qt.Horizontal)
        self.flow_slider.setRange(1, 100)
        self.flow_slider.setValue(self.brush.flow)
        brush_layout.addWidget(self.flow_slider)

        side_layout.addWidget(brush_panel)
        self.brush_preview = QLabel()
        self.brush_preview.setContentsMargins(0, 0, 0, 0)
        self.brush_preview.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 0px;
                margin: 0px;
            }
        """)
        self.brush_preview.setAlignment(Qt.AlignCenter)
        self.brush_preview.setFixedHeight(100)
        brush_layout.addWidget(self.brush_preview)
        side_layout.addWidget(brush_panel)

        master_label = QLabel("Master")
        master_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 11px;
                padding: 2px;
                color: #444;
                border-bottom: 1px solid #ddd;
                background: #f5f5f5;
            }
        """)
        master_label.setAlignment(Qt.AlignCenter)
        master_label.setFixedHeight(gui_constants.UI_SIZES['label_height'])
        side_layout.addWidget(master_label)
        self.master_thumbnail_frame = QFrame()
        self.master_thumbnail_frame.setObjectName("thumbnailContainer")
        self.master_thumbnail_frame.setStyleSheet(
            f"#thumbnailContainer{{ border: 2px solid {self.thumbnail_highlight}; }}")
        self.master_thumbnail_frame.setFrameShape(QFrame.StyledPanel)
        master_thumbnail_layout = QVBoxLayout(self.master_thumbnail_frame)
        master_thumbnail_layout.setContentsMargins(8, 8, 8, 8)
        self.master_thumbnail_label = QLabel()
        self.master_thumbnail_label.setAlignment(Qt.AlignCenter)
        self.master_thumbnail_label.setFixedWidth(
            gui_constants.UI_SIZES['thumbnail_width'])
        self.master_thumbnail_label.mousePressEvent = \
            lambda e: self.display_manager.set_view_master()
        self.master_thumbnail_label.setMouseTracking(True)

        def label_clicked(event):
            if event.button() == Qt.LeftButton:
                self.toggle_view_master_individual()

        self.master_thumbnail_label.mousePressEvent = label_clicked
        master_thumbnail_layout.addWidget(self.master_thumbnail_label)
        side_layout.addWidget(self.master_thumbnail_frame)
        side_layout.addSpacing(10)
        layers_label = QLabel("Layers")
        layers_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 11px;
                padding: 2px;
                color: #444;
                border-bottom: 1px solid #ddd;
                background: #f5f5f5;
            }
        """)
        layers_label.setAlignment(Qt.AlignCenter)
        layers_label.setFixedHeight(gui_constants.UI_SIZES['label_height'])
        side_layout.addWidget(layers_label)
        self.thumbnail_list = QListWidget()
        self.thumbnail_list.setFocusPolicy(Qt.StrongFocus)
        self.thumbnail_list.setViewMode(QListWidget.ListMode)
        self.thumbnail_list.setUniformItemSizes(True)
        self.thumbnail_list.setResizeMode(QListWidget.Adjust)
        self.thumbnail_list.setFlow(QListWidget.TopToBottom)
        self.thumbnail_list.setMovement(QListWidget.Static)
        self.thumbnail_list.setFixedWidth(gui_constants.THUMB_WIDTH)
        self.thumbnail_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.thumbnail_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        def change_layer_item(item):
            layer_idx = self.thumbnail_list.row(item)
            self.change_layer(layer_idx)

        self.thumbnail_list.itemClicked.connect(change_layer_item)
        self.thumbnail_list.setStyleSheet("""
            QListWidget {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
            }
            QListWidget::item {
                height: 130px;
                width: 110px;
            }
            QListWidget::item:selected {
                background-color: #e0e0e0;
                border: 1px solid #aaa;
            }
            QScrollBar:vertical {
                border: none;
                background: #f5f5f5;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #ccc;
                min-height: 20px;
                border-radius: 6px;
            }
        """)
        side_layout.addWidget(self.thumbnail_list, 1)
        control_panel = QWidget()
        layout.addWidget(self.image_viewer, 1)
        layout.addWidget(side_panel, 0)
        layout.addWidget(control_panel, 0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.display_manager = DisplayManager(
            self.layer_collection, self.image_viewer,
            self.master_thumbnail_label, self.thumbnail_list, parent=self)
        self.io_gui_handler = IOGuiHandler(self.layer_collection, self.undo_manager, parent=self)
        self.display_manager.status_message_requested.connect(self.show_status_message)
        self.display_manager.cursor_preview_state_changed.connect(
            lambda state: setattr(self.image_viewer, 'allow_cursor_preview', state))
        self.io_gui_handler.status_message_requested.connect(self.show_status_message)
        self.io_gui_handler.update_title_requested.connect(self.update_title)
        self.io_gui_handler.mark_as_modified_requested.connect(self.mark_as_modified)
        self.io_gui_handler.change_layer_requested.connect(self.change_layer)
        self.brush_tool.setup_ui(self.brush, self.brush_preview, self.image_viewer,
                                 self.brush_size_slider, self.hardness_slider, self.opacity_slider,
                                 self.flow_slider)
        self.image_viewer.brush = self.brush_tool.brush
        self.brush_tool.update_brush_thumb()
        self.io_gui_handler.setup_ui(self.display_manager, self.image_viewer)
        self.image_viewer.display_manager = self.display_manager

        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        file_menu.addAction("&Open...", self.io_gui_handler.open_file, "Ctrl+O")
        self.save_action = QAction("&Save", self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self.io_gui_handler.save_file)
        file_menu.addAction(self.save_action)
        self.save_as_action = QAction("Save &As...", self)
        self.save_as_action.setShortcut("Ctrl+Shift+S")
        self.save_as_action.triggered.connect(self.io_gui_handler.save_file_as)
        file_menu.addAction(self.save_as_action)
        self.io_gui_handler.save_master_only = QAction("Save Master &Only", self)
        self.io_gui_handler.save_master_only.setCheckable(True)
        self.io_gui_handler.save_master_only.setChecked(True)
        self.io_gui_handler.save_master_only.triggered.connect(self.save_master_only)
        file_menu.addAction(self.io_gui_handler.save_master_only)
        self.save_actions_set_enabled(False)

        file_menu.addAction("&Close", self.close_file, "Ctrl+W")
        file_menu.addSeparator()
        file_menu.addAction("&Import frames", self.io_gui_handler.import_frames)
        file_menu.addAction("Import &EXIF data", self.io_gui_handler.select_exif_path)

        edit_menu = menubar.addMenu("&Edit")
        self.undo_action = QAction("Undo", self)
        self.undo_action.setEnabled(False)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.triggered.connect(self.undo)
        edit_menu.addAction(self.undo_action)
        self.redo_action = QAction("Redo", self)
        self.redo_action.setEnabled(False)
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.triggered.connect(self.redo)
        edit_menu.addAction(self.redo_action)
        edit_menu.addSeparator()

        copy_action = QAction("Copy Layer to Master", self)
        copy_action.setShortcut("Ctrl+M")
        copy_action.triggered.connect(self.copy_layer_to_master)
        edit_menu.addAction(copy_action)

        view_menu = menubar.addMenu("&View")

        fullscreen_action = QAction("Full Screen", self)
        fullscreen_action.setShortcut("Ctrl+Cmd+F")
        fullscreen_action.setCheckable(True)
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)

        view_menu.addSeparator()

        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self.image_viewer.zoom_in)
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self.image_viewer.zoom_out)
        view_menu.addAction(zoom_out_action)

        adapt_action = QAction("Adapt to Screen", self)
        adapt_action.setShortcut("Ctrl+0")
        adapt_action.triggered.connect(self.image_viewer.reset_zoom)
        view_menu.addAction(adapt_action)

        actual_size_action = QAction("Actual Size", self)
        actual_size_action.setShortcut("Ctrl+=")
        actual_size_action.triggered.connect(self.image_viewer.actual_size)
        view_menu.addAction(actual_size_action)
        view_menu.addSeparator()

        view_master_action = QAction("View Master", self)
        view_master_action.setShortcut("M")
        view_master_action.triggered.connect(self.set_view_master)
        view_menu.addAction(view_master_action)

        view_individual_action = QAction("View Individual", self)
        view_individual_action.setShortcut("L")
        view_individual_action.triggered.connect(self.set_view_individual)
        view_menu.addAction(view_individual_action)

        toggle_view_master_individual_action = QAction("Toggle Master/Individual", self)
        toggle_view_master_individual_action.setShortcut("T")
        toggle_view_master_individual_action.triggered.connect(self.toggle_view_master_individual)
        view_menu.addAction(toggle_view_master_individual_action)
        view_menu.addSeparator()

        sort_asc_action = QAction("Sort Layers A-Z", self)
        sort_asc_action.triggered.connect(lambda: self.sort_layers('asc'))
        view_menu.addAction(sort_asc_action)

        sort_desc_action = QAction("Sort Layers Z-A", self)
        sort_desc_action.triggered.connect(lambda: self.sort_layers('desc'))
        view_menu.addAction(sort_desc_action)

        view_menu.addSeparator()

        cursor_menu = view_menu.addMenu("Cursor Style")

        brush_action = QAction("Simple Brush", self)
        brush_action.setCheckable(True)
        brush_action.setChecked(self.image_viewer.cursor_style == 'brush')
        brush_action.triggered.connect(lambda: self.image_viewer.set_cursor_style('brush'))
        cursor_menu.addAction(brush_action)

        preview_action = QAction("Brush Preview", self)
        preview_action.setCheckable(True)
        preview_action.setChecked(self.image_viewer.cursor_style == 'preview')
        preview_action.triggered.connect(lambda: self.image_viewer.set_cursor_style('preview'))
        cursor_menu.addAction(preview_action)

        outline_action = QAction("Outline Only", self)
        outline_action.setCheckable(True)
        outline_action.setChecked(self.image_viewer.cursor_style == 'outline')
        outline_action.triggered.connect(lambda: self.image_viewer.set_cursor_style('outline'))
        cursor_menu.addAction(outline_action)

        cursor_group = QActionGroup(self)
        cursor_group.addAction(preview_action)
        cursor_group.addAction(outline_action)
        cursor_group.addAction(brush_action)
        cursor_group.setExclusive(True)

        filter_menu = menubar.addMenu("&Filter")
        filter_menu.setObjectName("Filter")
        denoise_action = QAction("Denoise", self)
        denoise_action.triggered.connect(self.denoise_filter)
        filter_menu.addAction(denoise_action)
        unsharp_mask_action = QAction("Unsharp Mask", self)
        unsharp_mask_action.triggered.connect(self.unsharp_mask)
        filter_menu.addAction(unsharp_mask_action)
        white_balance_action = QAction("White Balance", self)
        white_balance_action.triggered.connect(self.white_balance)
        filter_menu.addAction(white_balance_action)
        vignetting_action = QAction("Vignetting correction", self)
        vignetting_action.triggered.connect(self.vignetting_correction)
        filter_menu.addAction(vignetting_action)

        help_menu = menubar.addMenu("&Help")
        help_menu.setObjectName("Help")
        shortcuts_help_action = QAction("Shortcuts and mouse", self)

        def shortcuts_help():
            self.shortcuts_help_dialog = ShortcutsHelp(self)
            self.shortcuts_help_dialog.exec()

        shortcuts_help_action.triggered.connect(shortcuts_help)
        help_menu.addAction(shortcuts_help_action)

        prev_layer = QShortcut(QKeySequence(Qt.Key_Up), self, context=Qt.ApplicationShortcut)
        prev_layer.activated.connect(self.prev_layer)
        next_layer = QShortcut(QKeySequence(Qt.Key_Down), self, context=Qt.ApplicationShortcut)
        next_layer.activated.connect(self.next_layer)
        self.installEventFilter(self)

    def update_title(self):
        title = constants.APP_TITLE
        if self.io_gui_handler is not None:
            path = self.io_gui_handler.current_file_path()
            if path != '':
                title += f" - {path.split('/')[-1]}"
                if self.modified:
                    title += " *"
        self.window().setWindowTitle(title)

    def show_status_message(self, message):
        self.statusBar().showMessage(message)

    def mark_as_modified(self, value=True):
        self.modified = value
        self.save_actions_set_enabled(value)
        self.update_title()

    def check_unsaved_changes(self) -> bool:
        if self.modified:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "The image stack has unsaved changes. Do you want to continue?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if reply == QMessageBox.Save:
                self.io_gui_handler.save_file()
                return True
            if reply == QMessageBox.Discard:
                return True
            return False
        return True

    # pylint: disable=C0103
    def keyPressEvent(self, event):
        if self.image_viewer.empty:
            return
        if event.text() == '[':
            self.brush_tool.decrease_brush_size()
            return
        if event.text() == ']':
            self.brush_tool.increase_brush_size()
            return
        if event.text() == '{':
            self.brush_tool.decrease_brush_hardness()
            return
        if event.text() == '}':
            self.brush_tool.increase_brush_hardness()
            return
        super().keyPressEvent(event)
    # pylint: enable=C0103

    def save_master_only(self, _checked):
        self.update_title()

    def sort_layers(self, order):
        self.sort_layers(order)
        self.display_manager.update_thumbnails()
        self.change_layer(self.current_layer())

    def change_layer(self, layer_idx):
        if 0 <= layer_idx < self.number_of_layers():
            view_state = self.image_viewer.get_view_state()
            self.set_current_layer_idx(layer_idx)
            self.display_manager.display_current_view()
            self.image_viewer.set_view_state(view_state)
            self.thumbnail_list.setCurrentRow(layer_idx)
            self.thumbnail_list.setFocus()
            self.image_viewer.update_brush_cursor()
            self.image_viewer.setFocus()

    def prev_layer(self):
        if self.layer_stack() is not None:
            new_idx = max(0, self.current_layer_idx() - 1)
            if new_idx != self.current_layer_idx():
                self.change_layer(new_idx)
                self.display_manager.highlight_thumbnail(new_idx)

    def next_layer(self):
        if self.layer_stack() is not None:
            new_idx = min(self.number_of_layers() - 1, self.current_layer_idx() + 1)
            if new_idx != self.current_layer_idx():
                self.change_layer(new_idx)
                self.display_manager.highlight_thumbnail(new_idx)

    def copy_layer_to_master(self):
        if self.layer_stack() is None or self.master_layer() is None:
            return
        reply = QMessageBox.question(
            self,
            "Confirm Copy",
            "Warning: the current master layer will be erased.\n\nDo you want to continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.set_master_layer(self.current_layer().copy())
            self.master_layer().setflags(write=True)
            self.display_manager.display_current_view()
            self.display_manager.update_thumbnails()
            self.mark_as_modified()
            self.statusBar().showMessage(f"Copied layer {self.current_layer_idx() + 1} to master")

    def copy_brush_area_to_master(self, view_pos):
        if self.layer_stack() is None or self.number_of_layers() == 0 \
           or not self.display_manager.allow_cursor_preview():
            return
        area = self.brush_tool.apply_brush_operation(
            self.master_layer_copy(),
            self.current_layer(),
            self.master_layer(), self.mask_layer,
            view_pos)
        self.undo_manager.extend_undo_area(*area)

    def begin_copy_brush_area(self, pos):
        if self.display_manager.allow_cursor_preview():
            self.mask_layer = self.io_gui_handler.blank_layer.copy()
            self.copy_master_layer()
            self.undo_manager.reset_undo_area()
            self.copy_brush_area_to_master(pos)
            self.display_manager.needs_update = True
            if not self.display_manager.update_timer.isActive():
                self.display_manager.update_timer.start()
            self.mark_as_modified()

    def continue_copy_brush_area(self, pos):
        if self.display_manager.allow_cursor_preview():
            self.copy_brush_area_to_master(pos)
            self.display_manager.needs_update = True
            if not self.display_manager.update_timer.isActive():
                self.display_manager.update_timer.start()
            self.mark_as_modified()

    def end_copy_brush_area(self):
        if self.display_manager.update_timer.isActive():
            self.display_manager.display_master_layer()
            self.display_manager.update_master_thumbnail()
            self.undo_manager.save_undo_state(self.master_layer_copy(), 'Brush Stroke')
            self.display_manager.update_timer.stop()
            self.mark_as_modified()

    def update_undo_redo_actions(self, has_undo, undo_desc, has_redo, redo_desc):
        if self.undo_action:
            if has_undo:
                self.undo_action.setText(f"Undo {undo_desc}")
                self.undo_action.setEnabled(True)
            else:
                self.undo_action.setText("Undo")
                self.undo_action.setEnabled(False)
        if self.redo_action:
            if has_redo:
                self.redo_action.setText(f"Redo {redo_desc}")
                self.redo_action.setEnabled(True)
            else:
                self.redo_action.setText("Redo")
                self.redo_action.setEnabled(False)

    def denoise_filter(self):
        self.filter_manager.apply("Denoise")

    def unsharp_mask(self):
        self.filter_manager.apply("Unsharp Mask")

    def white_balance(self, init_val=None):
        self.filter_manager.apply("White Balance", init_val=init_val or (128, 128, 128))

    def vignetting_correction(self):
        self.filter_manager.apply("Vignetting Correction")

    def connect_preview_toggle(self, preview_check, do_preview, restore_original):
        def on_toggled(checked):
            if checked:
                do_preview()
            else:
                restore_original()
        preview_check.toggled.connect(on_toggled)

    def get_pixel_color_at(self, pos, radius=None):
        item_pos = self.image_viewer.position_on_image(pos)
        x = int(item_pos.x())
        y = int(item_pos.y())
        master_layer = self.master_layer()
        if (0 <= x < self.master_layer().shape[1]) and \
           (0 <= y < self.master_layer().shape[0]):
            if radius is None:
                radius = int(self.brush.size)
            if radius > 0:
                y_indices, x_indices = np.ogrid[-radius:radius + 1, -radius:radius + 1]
                mask = x_indices**2 + y_indices**2 <= radius**2
                x0 = max(0, x - radius)
                x1 = min(master_layer.shape[1], x + radius + 1)
                y0 = max(0, y - radius)
                y1 = min(master_layer.shape[0], y + radius + 1)
                mask = mask[radius - (y - y0): radius + (y1 - y),
                            radius - (x - x0): radius + (x1 - x)]
                region = master_layer[y0:y1, x0:x1]
                if region.size == 0:
                    pixel = master_layer[y, x]
                else:
                    if region.ndim == 3:
                        pixel = [region[:, :, c][mask].mean() for c in range(region.shape[2])]
                    else:
                        pixel = region[mask].mean()
            else:
                pixel = self.master_layer()[y, x]
            if np.isscalar(pixel):
                pixel = [pixel, pixel, pixel]
            pixel = [np.float32(x) for x in pixel]
            if master_layer.dtype == np.uint16:
                pixel = [x / 256.0 for x in pixel]
            return tuple(int(v) for v in pixel)
        return (0, 0, 0)

    def highlight_master_thumbnail(self):
        self.master_thumbnail_frame.setStyleSheet(
            f"#thumbnailContainer{{ border: 2px solid {self.thumbnail_highlight}; }}")

    def save_actions_set_enabled(self, enabled):
        self.save_action.setEnabled(enabled)
        self.save_as_action.setEnabled(enabled)
        self.io_gui_handler.save_master_only.setEnabled(enabled)

    def close_file(self):
        if self.check_unsaved_changes():
            self.io_gui_handler.close_file()
            self.set_master_layer(None)
            self.mark_as_modified(False)

    def set_view_master(self):
        self.display_manager.set_view_master()
        self.thumbnail_highlight = gui_constants.THUMB_MASTER_HI_COLOR
        self.highlight_master_thumbnail()

    def set_view_individual(self):
        self.display_manager.set_view_individual()
        self.thumbnail_highlight = gui_constants.THUMB_MASTER_LO_COLOR
        self.highlight_master_thumbnail()

    def toggle_view_master_individual(self):
        if self.display_manager.view_mode == 'master':
            self.set_view_individual()
        else:
            self.set_view_master()

    def toggle_fullscreen(self, checked):
        if checked:
            self.window().showFullScreen()
        else:
            self.window().showNormal()

    def quit(self):
        if self.check_unsaved_changes():
            self.close()

    def undo(self):
        if self.undo_manager.undo(self.master_layer()):
            self.display_manager.display_current_view()
            self.display_manager.update_master_thumbnail()
            self.mark_as_modified()
            self.statusBar().showMessage("Undo applied", 2000)

    def redo(self):
        if self.undo_manager.redo(self.master_layer()):
            self.display_manager.display_current_view()
            self.display_manager.update_master_thumbnail()
            self.mark_as_modified()
            self.statusBar().showMessage("Redo applied", 2000)

    def handle_temp_view(self, start):
        if start:
            self.display_manager.start_temp_view()
            self.thumbnail_highlight = gui_constants.THUMB_MASTER_LO_COLOR
            self.highlight_master_thumbnail()
        else:
            self.display_manager.end_temp_view()
            self.thumbnail_highlight = gui_constants.THUMB_MASTER_HI_COLOR
            self.highlight_master_thumbnail()

    def handle_brush_size_change(self, delta):
        if delta > 0:
            self.brush_tool.increase_brush_size()
        else:
            self.brush_tool.decrease_brush_size()
