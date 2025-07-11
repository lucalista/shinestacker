from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QListWidget, QListWidgetItem, QSlider
from PySide6.QtGui import QShortcut, QKeySequence, QAction, QActionGroup
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QGuiApplication
from focusstack.retouch.image_editor import ImageEditor
from focusstack.retouch.image_viewer import ImageViewer
from focusstack.retouch.gui_constants import gui_constants


def brush_size_to_slider(size):
    if size <= gui_constants.BRUSH_SIZES['min']:
        return 0
    if size >= gui_constants.BRUSH_SIZES['max']:
        return gui_constants.BRUSH_SIZE_SLIDER_MAX
    normalized = ((size - gui_constants.BRUSH_SIZES['min']) / gui_constants.BRUSH_SIZES['max']) ** (1 / gui_constants.BRUSH_GAMMA)
    return int(normalized * gui_constants.BRUSH_SIZE_SLIDER_MAX)


class ImageEditorUI(ImageEditor):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_menu()
        self.setup_shortcuts()

    def setup_shortcuts(self):
        prev_layer = QShortcut(QKeySequence(Qt.Key_Up), self, context=Qt.ApplicationShortcut)
        prev_layer.activated.connect(self.prev_layer)
        next_layer = QShortcut(QKeySequence(Qt.Key_Down), self, context=Qt.ApplicationShortcut)
        next_layer.activated.connect(self.next_layer)

    def setup_ui(self):
        self.setWindowTitle(gui_constants.APP_TITLE)
        self.resize(1400, 900)
        center = QGuiApplication.primaryScreen().geometry().center()
        self.move(center - self.rect().center())
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        self.image_viewer = ImageViewer()
        self.image_viewer.temp_view_requested.connect(self.handle_temp_view)
        self.image_viewer.image_editor = self
        self.image_viewer.brush = self.brush_controller.brush
        self.image_viewer.setup_brush_cursor()
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
        self.brush_size_slider.valueChanged.connect(self.update_brush_size)
        brush_layout.addWidget(self.brush_size_slider)

        hardness_label = QLabel("Brush Hardness")
        hardness_label.setAlignment(Qt.AlignCenter)
        brush_layout.addWidget(hardness_label)
        self.hardness_slider = QSlider(Qt.Horizontal)
        self.hardness_slider.setRange(0, 100)
        self.hardness_slider.setValue(self.brush.hardness)
        self.hardness_slider.valueChanged.connect(self.update_brush_hardness)
        brush_layout.addWidget(self.hardness_slider)

        opacity_label = QLabel("Brush Opacity")
        opacity_label.setAlignment(Qt.AlignCenter)
        brush_layout.addWidget(opacity_label)
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(self.brush.opacity)
        self.opacity_slider.valueChanged.connect(self.update_brush_opacity)
        brush_layout.addWidget(self.opacity_slider)

        flow_label = QLabel("Brush Flow")
        flow_label.setAlignment(Qt.AlignCenter)
        brush_layout.addWidget(flow_label)
        self.flow_slider = QSlider(Qt.Horizontal)
        self.flow_slider.setRange(1, 100)
        self.flow_slider.setValue(self.brush.flow)
        self.flow_slider.valueChanged.connect(self.update_brush_flow)
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
        self.update_brush_thumb()
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
        self.master_thumbnail_label.setFixedSize(gui_constants.THUMB_WIDTH, gui_constants.THUMB_HEIGHT)
        self.master_thumbnail_label.mousePressEvent = lambda e: self.set_view_master()
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
        self.thumbnail_list.itemClicked.connect(self.change_layer_item)
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

    def setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        file_menu.addAction("&New", self.new_file, "Ctrl+N")
        file_menu.addAction("&Open...", self.open_file, "Ctrl+O")
        file_menu.addAction("&Save", self.save_file, "Ctrl+S")
        file_menu.addAction("Save &As...", self.save_file_as)
        file_menu.addSeparator()
        file_menu.addAction("Select &EXIF path", self.select_exif_path)

        edit_menu = menubar.addMenu("&Edit")
        undo_action = QAction("Undo Brush", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.undo_last_brush)
        edit_menu.addAction(undo_action)
        edit_menu.addSeparator()

        copy_action = QAction("Copy Layer to Master", self)
        copy_action.setShortcut("Ctrl+M")
        copy_action.triggered.connect(self.copy_layer_to_master)
        edit_menu.addAction(copy_action)

        view_menu = menubar.addMenu("&View")
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
        view_menu.addSeparator()

        sort_asc_action = QAction("Sort Layers A-Z", self)
        sort_asc_action.triggered.connect(lambda: self.sort_layers('asc'))
        view_menu.addAction(sort_asc_action)

        sort_desc_action = QAction("Sort Layers Z-A", self)
        sort_desc_action.triggered.connect(lambda: self.sort_layers('desc'))
        view_menu.addAction(sort_desc_action)

        sort_original_action = QAction("Original Order", self)
        sort_original_action.triggered.connect(lambda: self.sort_layers('original'))
        view_menu.addAction(sort_original_action)
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

    def quit(self):
        if self._check_unsaved_changes():
            self.close()

    def _add_thumbnail_item(self, thumbnail, label, is_current):
        item_widget = QWidget()
        layout = QVBoxLayout(item_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        thumbnail_label = QLabel()
        thumbnail_label.setPixmap(thumbnail)
        thumbnail_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(thumbnail_label)

        label_widget = QLabel(label)
        label_widget.setAlignment(Qt.AlignCenter)
        layout.addWidget(label_widget)

        item = QListWidgetItem()
        item.setSizeHint(QSize(gui_constants.IMG_WIDTH, gui_constants.IMG_HEIGHT))
        self.thumbnail_list.addItem(item)
        self.thumbnail_list.setItemWidget(item, item_widget)

        if is_current:
            self.thumbnail_list.setCurrentItem(item)

    def undo_last_brush(self):
        if self.undo_manager.undo(self.master_layer):
            self.display_current_view()
            self.mark_as_modified()
            self.statusBar().showMessage("Undo applied", 2000)

    def handle_temp_view(self, start):
        if start:
            self.start_temp_view()
        else:
            self.end_temp_view()
