# pylint: disable=C0114, C0115, C0116, E0611, R0902, R0914, R0915
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
                               QListWidget, QSlider)
from PySide6.QtGui import QShortcut, QKeySequence, QAction, QActionGroup
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from .. config.gui_constants import gui_constants
from .image_filters import ImageFilters
from .image_viewer import ImageViewer
from .shortcuts_help import ShortcutsHelp
from .brush import Brush


def brush_size_to_slider(size):
    if size <= gui_constants.BRUSH_SIZES['min']:
        return 0
    if size >= gui_constants.BRUSH_SIZES['max']:
        return gui_constants.BRUSH_SIZE_SLIDER_MAX
    normalized = ((size - gui_constants.BRUSH_SIZES['min']) /
                  gui_constants.BRUSH_SIZES['max']) ** (1 / gui_constants.BRUSH_GAMMA)
    return int(normalized * gui_constants.BRUSH_SIZE_SLIDER_MAX)


class ImageEditorUI(ImageFilters):
    def __init__(self):
        super().__init__()
        self.brush = Brush()
        self.setup_ui()
        self.setup_menu()
        self.setup_shortcuts()
        self._dialog = None

    def setup_shortcuts(self):
        prev_layer = QShortcut(QKeySequence(Qt.Key_Up), self, context=Qt.ApplicationShortcut)
        prev_layer.activated.connect(self.prev_layer)
        next_layer = QShortcut(QKeySequence(Qt.Key_Down), self, context=Qt.ApplicationShortcut)
        next_layer.activated.connect(self.next_layer)

    def setup_ui(self):
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
        master_label.setFixedHeight(gui_constants.LABEL_HEIGHT)
        side_layout.addWidget(master_label)
        self.master_thumbnail_frame = QFrame()
        self.master_thumbnail_frame.setFrameShape(QFrame.StyledPanel)
        master_thumbnail_layout = QVBoxLayout(self.master_thumbnail_frame)
        master_thumbnail_layout.setContentsMargins(2, 2, 2, 2)
        self.master_thumbnail_label = QLabel()
        self.master_thumbnail_label.setAlignment(Qt.AlignCenter)
        self.master_thumbnail_label.setFixedSize(
            gui_constants.THUMB_WIDTH, gui_constants.THUMB_HEIGHT)
        self.master_thumbnail_label.mousePressEvent = \
            lambda e: self.display_manager.set_view_master()
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
        layers_label.setFixedHeight(gui_constants.LABEL_HEIGHT)
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
        super().setup_ui()

    def setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        file_menu.addAction("&Open...", self.io_gui_handler.open_file, "Ctrl+O")
        file_menu.addAction("&Save", self.io_gui_handler.save_file, "Ctrl+S")
        file_menu.addAction("Save &As...", self.io_gui_handler.save_file_as, "Ctrl+Shift+S")
        self.save_master_only = QAction("Save Master &Only", self)
        self.save_master_only.setCheckable(True)
        self.save_master_only.setChecked(True)
        file_menu.addAction(self.save_master_only)

        file_menu.addAction("&Close", self.io_gui_handler.close_file, "Ctrl+W")
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
        view_master_action.triggered.connect(self.display_manager.set_view_master)
        view_menu.addAction(view_master_action)

        view_individual_action = QAction("View Individual", self)
        view_individual_action.setShortcut("L")
        view_individual_action.triggered.connect(self.display_manager.set_view_individual)
        view_menu.addAction(view_individual_action)
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

        help_menu = menubar.addMenu("&Help")
        help_menu.setObjectName("Help")
        shortcuts_help_action = QAction("Shortcuts and mouse", self)
        shortcuts_help_action.triggered.connect(self.shortcuts_help)
        help_menu.addAction(shortcuts_help_action)

    def shortcuts_help(self):
        self._dialog = ShortcutsHelp(self)
        self._dialog.exec()

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
        else:
            self.display_manager.end_temp_view()

    def handle_brush_size_change(self, delta):
        if delta > 0:
            self.brush_tool.increase_brush_size()
        else:
            self.brush_tool.decrease_brush_size()
