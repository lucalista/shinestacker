import webbrowser
import numpy as np
import tifffile
import zlib
from psdtags import PsdChannelId
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QListWidgetItem, QListWidget,
                               QSlider, QFileDialog, QMessageBox, QAbstractItemView)
from PySide6.QtGui import (QPixmap, QPainter, QColor, QImage, QPen, QBrush, QShortcut, QKeySequence,
                           QAction, QRadialGradient, QActionGroup)
from PySide6.QtCore import Qt, QTimer, QEvent, QSize, QDateTime, QPoint
from algorithms.multilayer import read_multilayer_tiff, write_multilayer_tiff_from_images
from gui.image_viewer import ImageViewer

DONT_USE_NATIVE_MENU = True

LABEL_HEIGHT = 20
THUMB_WIDTH = 120
THUMB_HEIGHT = 80
IMG_WIDTH = 100
IMG_HEIGHT = 80
DEFAULT_BRUSH_HARDNESS = 25
PAINT_REFRESH_TIMER = 200  # milliseconds
MIN_ZOOMED_IMG_WIDTH = 400
MAX_ZOOMED_IMG_PX_SIZE = 50

BRUSH_COLORS = {
    'outer': QColor(255, 0, 0, 200),  # Bordo esterno rosso
    'inner': QColor(255, 0, 0, 150),  # Rosso semi-trasparente
    'gradient_end': QColor(255, 0, 0, 0),  # Rosso completamente trasparente
    'pen': QColor(255, 0, 0, 150),  # Colore della penna
    'preview': QColor(255, 180, 180),  # Colore di preview
    'cursor_inner': QColor(255, 0, 0, 120),  # Rosso per il cursore
    'preview_inner': QColor(255, 255, 255, 150)  # Bianco per l'anteprima reale
}

PREVIEW_OPACITY = 180  # Opacità per l'anteprima del layer

UI_SIZES = {
    'brush_preview': (100, 80),
    'thumbnail': (IMG_WIDTH, IMG_HEIGHT),
    'master_thumb': (THUMB_WIDTH, THUMB_HEIGHT)
}

BRUSH_SIZE_SLIDER_MAX = 1000
BRUSH_SIZES = {
    'default': 50,
    'min': 4,
    'mid': 50,
    'max': 1000
}

DEFAULT_BRUSH_OPACITY = 100
MIN_BRUSH_OPACITY = 20


def calculate_gamma():
    if BRUSH_SIZES['mid'] <= BRUSH_SIZES['min'] or BRUSH_SIZES['max'] <= 0:
        return 1.0
    ratio = (BRUSH_SIZES['mid'] - BRUSH_SIZES['min']) / BRUSH_SIZES['max']
    half_point = BRUSH_SIZE_SLIDER_MAX / 2
    if ratio <= 0:
        return 1.0
    gamma = np.log(ratio) / np.log(half_point / BRUSH_SIZE_SLIDER_MAX)
    return gamma


BRUSH_GAMMA = calculate_gamma()


def slider_to_brush_size(slider_val):
    normalized = slider_val / BRUSH_SIZE_SLIDER_MAX
    size = BRUSH_SIZES['min'] + BRUSH_SIZES['max'] * (normalized ** BRUSH_GAMMA)
    return max(BRUSH_SIZES['min'], min(BRUSH_SIZES['max'], size))


def brush_size_to_slider(size):
    if size <= BRUSH_SIZES['min']:
        return 0
    if size >= BRUSH_SIZES['max']:
        return BRUSH_SIZE_SLIDER_MAX
    normalized = ((size - BRUSH_SIZES['min']) / BRUSH_SIZES['max']) ** (1 / BRUSH_GAMMA)
    return int(normalized * BRUSH_SIZE_SLIDER_MAX)


def create_brush_gradient(center_x, center_y, radius, hardness, inner_color=None, outer_color=None, opacity=100):
    gradient = QRadialGradient(center_x, center_y, float(radius))
    inner = inner_color if inner_color is not None else BRUSH_COLORS['inner']
    outer = outer_color if outer_color is not None else BRUSH_COLORS['gradient_end']
    inner_with_opacity = QColor(inner)
    inner_with_opacity.setAlpha(int(float(inner.alpha()) * float(opacity) / 100.0))
    if hardness < 100:
        hardness_normalized = float(hardness) / 100.0
        gradient.setColorAt(0.0, inner_with_opacity)
        gradient.setColorAt(hardness_normalized, inner_with_opacity)
        gradient.setColorAt(1.0, outer)
    else:
        gradient.setColorAt(0.0, inner_with_opacity)
        gradient.setColorAt(1.0, inner_with_opacity)
    return gradient


def calculate_brush_mask(radius, hardness_percent):
    y, x = np.ogrid[-radius:radius + 1, -radius:radius + 1]
    distance = np.sqrt(x**2.0 + y**2.0)
    if hardness_percent <= 0:
        return (distance <= radius).astype(float)
    hardness_radius = radius * (hardness_percent / 100.0)
    if hardness_radius >= radius:
        return np.ones_like(distance, dtype=float)
    with np.errstate(divide='ignore', invalid='ignore'):
        mask = np.clip(1.0 - (distance - hardness_radius) / max(1e-10, (radius - hardness_radius)), 0.0, 1.0)
        mask[np.isnan(mask)] = 1.0
    return mask


class ImageEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_stack = None
        self.master_layer = None
        self.current_layer = 0
        self.brush_size = BRUSH_SIZES['default']
        self.brush_hardness = DEFAULT_BRUSH_HARDNESS
        self.brush_opacity = DEFAULT_BRUSH_OPACITY
        self._brush_mask_cache = {}
        self.cursor_style = 'preview'
        self.view_mode = 'master'
        self.temp_view_individual = False
        self.current_file_path = None
        self.modified = False
        self.undo_stack = []
        self.max_undo_steps = 50
        self.sort_order = 'original'
        self.setup_ui()
        self.setup_menu()
        self.setup_shortcuts()
        self.installEventFilter(self)
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(PAINT_REFRESH_TIMER)
        self.update_timer.timeout.connect(self.process_pending_updates)
        self.needs_update = False

    def process_pending_updates(self):
        if self.needs_update:
            self.display_current_view()
            self.mark_as_modified()
            self.needs_update = False

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_X:
            self.start_temp_view()
            return True
        elif event.type() == QEvent.KeyRelease and event.key() == Qt.Key_X:
            self.end_temp_view()
            return True
        return super().eventFilter(obj, event)

    def setup_shortcuts(self):
        prev_layer = QShortcut(QKeySequence(Qt.Key_Up), self, context=Qt.ApplicationShortcut)
        prev_layer.activated.connect(self.prev_layer)
        next_layer = QShortcut(QKeySequence(Qt.Key_Down), self, context=Qt.ApplicationShortcut)
        next_layer.activated.connect(self.next_layer)

    def setup_ui(self):
        self.setWindowTitle("Focus Stack Editor")
        self.resize(1400, 900)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        self.image_viewer = ImageViewer()
        self.image_viewer.image_editor = self
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
        self.brush_size_slider.setRange(0, BRUSH_SIZE_SLIDER_MAX)
        self.brush_size_slider.setValue(brush_size_to_slider(self.brush_size))
        self.brush_size_slider.valueChanged.connect(self.update_brush_size)
        brush_layout.addWidget(self.brush_size_slider)
        hardness_label = QLabel("Brush Hardness")
        hardness_label.setAlignment(Qt.AlignCenter)
        brush_layout.addWidget(hardness_label)

        self.hardness_slider = QSlider(Qt.Horizontal)
        self.hardness_slider.setRange(1, 100)
        self.hardness_slider.setValue(self.brush_hardness)
        self.hardness_slider.valueChanged.connect(self.update_brush_hardness)
        brush_layout.addWidget(self.hardness_slider)

        opacity_label = QLabel("Brush Opacity")
        opacity_label.setAlignment(Qt.AlignCenter)
        brush_layout.addWidget(opacity_label)

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(self.brush_opacity)
        self.opacity_slider.valueChanged.connect(self.update_brush_opacity)
        brush_layout.addWidget(self.opacity_slider)

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
        self.update_brush_preview()
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
        master_label.setFixedHeight(LABEL_HEIGHT)
        side_layout.addWidget(master_label)
        self.master_thumbnail_frame = QFrame()
        self.master_thumbnail_frame.setFrameShape(QFrame.StyledPanel)
        master_thumbnail_layout = QVBoxLayout(self.master_thumbnail_frame)
        master_thumbnail_layout.setContentsMargins(2, 2, 2, 2)
        self.master_thumbnail_label = QLabel()
        self.master_thumbnail_label.setAlignment(Qt.AlignCenter)
        self.master_thumbnail_label.setFixedSize(THUMB_WIDTH, THUMB_HEIGHT)
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
        layers_label.setFixedHeight(LABEL_HEIGHT)
        side_layout.addWidget(layers_label)
        self.thumbnail_list = QListWidget()
        self.thumbnail_list.setFocusPolicy(Qt.StrongFocus)
        self.thumbnail_list.setViewMode(QListWidget.ListMode)
        self.thumbnail_list.setUniformItemSizes(True)
        self.thumbnail_list.setResizeMode(QListWidget.Adjust)
        self.thumbnail_list.setFlow(QListWidget.TopToBottom)
        self.thumbnail_list.setMovement(QListWidget.Static)
        self.thumbnail_list.setFixedWidth(THUMB_WIDTH)
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
        file_menu.addAction("Open...", self.open_file, "Ctrl+O")
        file_menu.addAction("Save", self.save_file, "Ctrl+S")
        file_menu.addAction("Save As...", self.save_file_as)
        file_menu.addSeparator()
        if DONT_USE_NATIVE_MENU:
            quit_txt, quit_short = "&Quit", "Ctrl+Q"
        else:
            quit_txt, quit_short = "Shut dw&wn", "Ctrl+W"
        exit_action = QAction(quit_txt, self)
        exit_action.setShortcut(quit_short)
        exit_action.triggered.connect(self.quit)
        file_menu.addAction(exit_action)

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

        # Nel setup_menu:
        brush_action = QAction("Simple Brush", self)
        brush_action.setCheckable(True)
        brush_action.setChecked(self.cursor_style == 'brush')
        brush_action.triggered.connect(lambda: self.set_cursor_style('brush'))
        cursor_menu.addAction(brush_action)

        preview_action = QAction("Brush Preview", self)
        preview_action.setCheckable(True)
        preview_action.setChecked(self.cursor_style == 'preview')
        preview_action.triggered.connect(lambda: self.set_cursor_style('preview'))
        cursor_menu.addAction(preview_action)

        outline_action = QAction("Outline Only", self)
        outline_action.setCheckable(True)
        outline_action.setChecked(self.cursor_style == 'outline')
        outline_action.triggered.connect(lambda: self.set_cursor_style('outline'))
        cursor_menu.addAction(outline_action)

        cursor_group = QActionGroup(self)
        cursor_group.addAction(preview_action)
        cursor_group.addAction(outline_action)
        cursor_group.addAction(brush_action)
        cursor_group.setExclusive(True)

        help_menu = menubar.addMenu("&Help")
        help_action = QAction("Online Help", self)
        help_action.triggered.connect(self.website)
        help_menu.addAction(help_action)

    def quit(self):
        if self._check_unsaved_changes():
            self.close()

    def _check_unsaved_changes(self) -> bool:
        if self.modified:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "The image stack has unsaved changes. Do you want to continue?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if reply == QMessageBox.Save:
                self._save_file()
                return True
            elif reply == QMessageBox.Discard:
                return True
            else:
                return False
        else:
            return True

    def website(self):
        webbrowser.open("https://github.com/lucalista/focusstack/blob/main/docs/main.md")

    def sort_layers(self, order):
        if not hasattr(self, 'current_stack') or not hasattr(self, 'current_labels'):
            return
        self.sort_order = order
        if order == 'original':
            if self.current_file_path:
                self.current_stack, self.current_labels = self.load_tiff_stack(self.current_file_path)
                self.update_thumbnails()
                if self.current_layer >= len(self.current_stack):
                    self.current_layer = len(self.current_stack) - 1
                self.change_layer(self.current_layer)
            return
        master_index = -1
        master_label = None
        master_layer = None
        for i, label in enumerate(self.current_labels):
            if label.lower() == "master":
                master_index = i
                master_label = self.current_labels.pop(i)
                master_layer = self.current_stack[i]
                self.current_stack = np.delete(self.current_stack, i, axis=0)
                break
        if order == 'asc':
            sorted_indices = sorted(range(len(self.current_labels)),
                                    key=lambda i: self.current_labels[i].lower())
        else:
            sorted_indices = sorted(range(len(self.current_labels)),
                                    key=lambda i: self.current_labels[i].lower(),
                                    reverse=True)
        self.current_labels = [self.current_labels[i] for i in sorted_indices]
        self.current_stack = self.current_stack[sorted_indices]
        if master_index != -1:
            self.current_labels.insert(0, master_label)
            self.current_stack = np.insert(self.current_stack, 0, master_layer, axis=0)
            self.master_layer = master_layer.copy()
        self.update_thumbnails()
        if self.current_layer >= len(self.current_stack):
            self.current_layer = len(self.current_stack) - 1
        self.change_layer(self.current_layer)

    def load_tiff_stack(self, path):
        try:
            psd_data = read_multilayer_tiff(path)
            layers = []
            labels = []
            for layer in reversed(psd_data.layers.layers):
                channels = {}
                for channel in layer.channels:
                    channels[channel.channelid] = channel.data
                if PsdChannelId.CHANNEL0 in channels:
                    img = np.stack([
                        channels[PsdChannelId.CHANNEL0],
                        channels[PsdChannelId.CHANNEL1],
                        channels[PsdChannelId.CHANNEL2]
                    ], axis=-1)
                    layers.append(img)
                    labels.append(layer.name)
            if layers:
                stack = np.array(layers)
                if labels:
                    master_indices = [i for i, label in enumerate(labels) if label.lower() == "master"]
                    if master_indices:
                        master_index = master_indices[0]
                        master_label = labels.pop(master_index)
                        master_layer = stack[master_index]
                        stack = np.delete(stack, master_index, axis=0)
                        labels.insert(0, master_label)
                        stack = np.insert(stack, 0, master_layer, axis=0)
                    return stack, labels
                return stack, labels
        except Exception:
            try:
                stack = tifffile.imread(path)
                if stack.ndim == 3:
                    return stack, None
                return None, None
            except Exception:
                return None, None

    def open_file(self, path=None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(
                self, "Open Image", "", "Images (*.tif *.tiff *.png *.jpg)")
        if path:
            self.current_file_path = path
            self.current_stack, self.current_labels = self.load_tiff_stack(path)
            if self.current_stack is not None and len(self.current_stack) > 0:
                master_indices = [i for i, label in enumerate(self.current_labels) if label.lower() == "master"]
                master_index = -1 if len(master_indices) == 0 else master_indices[0]
                if master_index == -1:
                    self.master_layer = self.current_stack[0].copy()
                else:
                    self.current_labels.pop(master_index)
                    self.master_layer = self.current_stack[master_index].copy()
                    indices = list(range(len(self.current_stack)))
                    indices.remove(master_index)
                    self.current_stack = self.current_stack[indices]
                if self.current_labels is None:
                    self.current_labels = [f"Layer {i + 1}" for i in range(len(self.current_stack))]
            self.update_thumbnails()
            self.change_layer(0)
            self.image_viewer.reset_zoom()
            self.statusBar().showMessage(f"Loaded: {path}")
            self.thumbnail_list.setFocus()

    def mark_as_modified(self):
        self.modified = True
        title = "Focus Stack Editor"
        if self.current_file_path:
            title += f" - {self.current_file_path}"
        self.setWindowTitle(title + "*")

    def save_file(self):
        if self.current_stack is None:
            return
        if self.current_file_path:
            self._save_to_path(self.current_file_path)
            self.modified = False
            self.setWindowTitle("Focus Stack Editor")
        else:
            self.save_file_as()

    def save_file_as(self):
        if self.current_stack is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Image", "",
                                              "TIFF Files (*.tif *.tiff);;All Files (*)")
        if path:
            if not path.lower().endswith(('.tif', '.tiff')):
                path += '.tiff'
            self._save_to_path(path)
            self.current_file_path = path
            self.statusBar().showMessage(f"Saved: {path}")

    def _save_to_path(self, path):
        try:
            master_layer = {'Master': self.master_layer}
            individual_layers = {label: image for label, image in zip(self.current_labels, self.current_stack)}
            write_multilayer_tiff_from_images({**individual_layers, **master_layer}, path)
            self.statusBar().showMessage(f"Saved: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save file: {str(e)}")

    def set_view_master(self):
        self.view_mode = 'master'
        self.temp_view_individual = False
        self.display_current_view()
        self.statusBar().showMessage("View mode: Master")

    def set_view_individual(self):
        self.view_mode = 'individual'
        self.temp_view_individual = False
        self.display_current_view()
        self.statusBar().showMessage("View mode: Individual layers")

    def start_temp_view(self):
        if not self.temp_view_individual and self.view_mode == 'master':
            self.temp_view_individual = True
            self.display_current_view()
            self.statusBar().showMessage("Temporary view: Individual layer (hold X)")

    def end_temp_view(self):
        if self.temp_view_individual:
            self.temp_view_individual = False
            self.display_current_view()
            self.statusBar().showMessage("View mode: Master")

    def display_current_view(self):
        """Mostra l'immagine corretta in base alla modalità di visualizzazione"""
        if self.temp_view_individual or self.view_mode == 'individual':
            self.display_current_layer()
        else:
            self.display_master_layer()

    def display_master_layer(self):
        """Mostra il layer master"""
        if self.master_layer is not None:
            qimage = self.numpy_to_qimage(self.master_layer)
            self.image_viewer.set_image(qimage)
            self.update_thumbnails()

    def create_thumbnail(self, layer, size):
        """Crea una miniatura automaticamente rilevando se è RGB o scala di grigi"""
        if layer.ndim == 3 and layer.shape[-1] == 3:
            return self.create_rgb_thumbnail(layer)
        else:
            return self.create_grayscale_thumbnail(layer)

    def update_thumbnails(self):
        if not hasattr(self, 'master_layer') or self.master_layer is None:
            return
        thumb_size = UI_SIZES['thumbnail']
        master_thumb = self.create_thumbnail(self.master_layer, thumb_size)
        self.master_thumbnail_label.setPixmap(master_thumb)
        self.thumbnail_list.clear()
        if self.current_stack is None:
            return
        for i, (layer, label) in enumerate(zip(self.current_stack, self.current_labels)):
            thumbnail = self.create_thumbnail(layer, thumb_size)
            self._add_thumbnail_item(thumbnail, label, i == self.current_layer)

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
        item.setSizeHint(QSize(IMG_WIDTH, IMG_HEIGHT))
        self.thumbnail_list.addItem(item)
        self.thumbnail_list.setItemWidget(item, item_widget)

        if is_current:
            self.thumbnail_list.setCurrentItem(item)

    def create_rgb_thumbnail(self, layer):
        if layer.dtype == np.uint16:
            layer = (layer // 256).astype(np.uint8)
        height, width, _ = layer.shape
        qimg = QImage(layer.data, width, height, 3 * width, QImage.Format_RGB888)
        return QPixmap.fromImage(qimg.scaled(*UI_SIZES['thumbnail'], Qt.KeepAspectRatio))

    def create_grayscale_thumbnail(self, layer):
        if layer.dtype == np.uint16:
            p2, p98 = np.percentile(layer, (2, 98))
            layer = np.clip(np.multiply(np.subtract(layer, p2), 255.0 / (p98 - p2)), 0, 255).astype(np.uint8)
        height, width = layer.shape
        qimg = QImage(layer.data, width, height, width, QImage.Format_Grayscale8)
        return QPixmap.fromImage(qimg.scaled(*UI_SIZES['thumbnail'], Qt.KeepAspectRatio))

    def change_layer(self, layer_idx):
        if 0 <= layer_idx < len(self.current_stack):
            view_state = self.image_viewer.get_view_state()
            self.current_layer = layer_idx
            self.display_current_view()
            self.image_viewer.set_view_state(view_state)
            self.thumbnail_list.setCurrentRow(layer_idx)
            self.thumbnail_list.setFocus()
            self.image_viewer.update_brush_cursor(self.brush_size)
            self.image_viewer.setFocus()

    def change_layer_item(self, item):
        layer_idx = self.thumbnail_list.row(item)
        self.change_layer(layer_idx)

    def display_current_layer(self):
        if self.current_stack is None:
            return
        layer = self.current_stack[self.current_layer]
        qimage = self.numpy_to_qimage(layer)
        self.image_viewer.set_image(qimage)

    def numpy_to_qimage(self, array):
        if array.dtype == np.uint16:
            array = np.right_shift(array, 8).astype(np.uint8)  # Più efficiente di divisione

        if array.ndim == 2:
            height, width = array.shape
            # Usare memoryview per evitare copie
            return QImage(memoryview(array), width, height, width, QImage.Format_Grayscale8)
        elif array.ndim == 3:
            height, width, _ = array.shape
            # Assicurarsi che l'array sia contiguous
            if not array.flags['C_CONTIGUOUS']:
                array = np.ascontiguousarray(array)
            return QImage(memoryview(array), width, height, 3 * width, QImage.Format_RGB888)
        return QImage()

    def prev_layer(self):
        if self.current_stack is not None:
            new_idx = max(0, self.current_layer - 1)
            if new_idx != self.current_layer:
                self.change_layer(new_idx)
                self.highlight_thumbnail(new_idx)

    def next_layer(self):
        if self.current_stack is not None:
            new_idx = min(len(self.current_stack) - 1, self.current_layer + 1)
            if new_idx != self.current_layer:
                self.change_layer(new_idx)
                self.highlight_thumbnail(new_idx)

    def highlight_thumbnail(self, index):
        self.thumbnail_list.setCurrentRow(index)
        self.thumbnail_list.scrollToItem(self.thumbnail_list.item(index),
                                         QAbstractItemView.PositionAtCenter)

    def update_brush_size(self, slider_val):
        self.brush_size = slider_to_brush_size(slider_val)
        self.update_brush_preview()
        self.image_viewer.update_brush_cursor(self.brush_size)
        self.clear_brush_cache()

    def update_brush_hardness(self, hardness):
        self.brush_hardness = max(1, min(100, hardness))
        self.update_brush_preview()
        self.image_viewer.update_brush_cursor(self.brush_size)
        self.clear_brush_cache()

    def update_brush_opacity(self, opacity):
        self.brush_opacity = opacity
        self.update_brush_preview()
        self.image_viewer.update_brush_cursor(self.brush_size)

    def update_brush_preview(self):
        width, height = UI_SIZES['brush_preview']
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        preview_size = min(self.brush_size, width + 30, height + 30)
        center_x, center_y = width // 2, height // 2
        gradient = create_brush_gradient(
            center_x, center_y, preview_size // 2,
            self.brush_hardness,
            inner_color=BRUSH_COLORS['inner'],
            outer_color=BRUSH_COLORS['gradient_end'],
            opacity=self.brush_opacity
        )
        painter.setPen(QPen(BRUSH_COLORS['outer'], 1))
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(QPoint(center_x, center_y), preview_size // 2, preview_size // 2)
        painter.setPen(QPen(QColor(0, 0, 160)))
        painter.drawText(0, 10, f"Size: {int(self.brush_size)}px")
        painter.drawText(0, 25, f"Hardness: {self.brush_hardness}%")
        painter.drawText(0, 40, f"Opacity: {self.brush_opacity}%")
        painter.end()
        self.brush_preview.setPixmap(pixmap)

    def clear_brush_cache(self):
        self._brush_mask_cache.clear()

    def copy_layer_to_master(self):
        if self.current_stack is None or self.master_layer is None:
            return
        reply = QMessageBox.question(
            self,
            "Confirm Copy",
            "Warning: the current master layer will be erased\n\nDo you want to continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.master_layer = self.current_stack[self.current_layer].copy()
            self.display_current_view()
            self.update_thumbnails()
            self.mark_as_modified()
            self.statusBar().showMessage(f"Copied layer {self.current_layer + 1} to master")

    def copy_brush_area_to_master(self, view_pos, continuous=False):
        if self.current_stack is None or self.master_layer is None or self.view_mode != 'master' or self.temp_view_individual:
            return
        if not continuous and not self.image_viewer.dragging:
            self.save_undo_state()
        scene_pos = self.image_viewer.mapToScene(view_pos)
        x_center = int(round(scene_pos.x()))
        y_center = int(round(scene_pos.y()))
        radius = int(round(self.brush_size // 2))
        h, w = self.master_layer.shape[:2]
        x_start = max(0, x_center - radius)
        y_start = max(0, y_center - radius)
        x_end = min(w, x_center + radius + 1)
        y_end = min(h, y_center + radius + 1)
        if x_start >= x_end or y_start >= y_end:
            return
        mask_key = (radius, self.brush_hardness)
        if mask_key not in self._brush_mask_cache:
            if self.brush_hardness <= 0:
                y, x = np.ogrid[-radius:radius + 1, -radius:radius + 1]
                mask = (x**2 + y**2 <= radius**2).astype(float)
            else:
                mask = calculate_brush_mask(radius, self.brush_hardness)
            self._brush_mask_cache[mask_key] = mask
        full_mask = self._brush_mask_cache[mask_key]
        mask = full_mask[
            y_start - (y_center - radius):y_end - (y_center - radius),
            x_start - (x_center - radius):x_end - (x_center - radius)
        ]
        opacity_factor = float(self.brush_opacity) / 100.0
        mask = np.clip(mask * opacity_factor, 0, 1)
        master_area = self.master_layer[y_start:y_end, x_start:x_end]
        layer_area = self.current_stack[self.current_layer][y_start:y_end, x_start:x_end]
        dtype = self.master_layer.dtype
        max_px_value = 65535 if dtype == np.uint16 else 255
        self.master_layer[y_start:y_end, x_start:x_end] = np.clip(
            master_area * (1 - mask[..., None] if master_area.ndim == 3 else 1 - mask) + # noqa
            layer_area * (mask[..., None] if master_area.ndim == 3 else mask),
            0, max_px_value
        ).astype(dtype)
        if not continuous:
            self.display_current_view()
            self.mark_as_modified()
        else:
            self.needs_update = True
            if not self.update_timer.isActive():
                self.update_timer.start()

    def save_undo_state(self):
        if self.master_layer is None:
            return

        # Usare la compressione zlib per ridurre l'uso di memoria
        current_state = zlib.compress(self.master_layer.tobytes())

        if self.undo_stack:
            # Evitare duplicati consecutivi
            if zlib.decompress(self.undo_stack[-1]['master']) == self.master_layer.tobytes():
                return

        undo_state = {
            'master': current_state,
            'shape': self.master_layer.shape,
            'dtype': self.master_layer.dtype,
            'timestamp': QDateTime.currentDateTime()
        }

        if len(self.undo_stack) >= self.max_undo_steps:
            self.undo_stack.pop(0)
        self.undo_stack.append(undo_state)

    def undo_last_brush(self):
        if not self.undo_stack or self.master_layer is None:
            return

        undo_state = self.undo_stack.pop()
        decompressed = zlib.decompress(undo_state['master'])
        self.master_layer = np.frombuffer(decompressed, dtype=undo_state['dtype'])
        self.master_layer = self.master_layer.reshape(undo_state['shape'])

        self.display_current_view()
        self.mark_as_modified()
        self.statusBar().showMessage("Undo applied", 2000)

    def set_cursor_style(self, style):
        self.cursor_style = style
        if self.image_viewer.brush_cursor:
            self.image_viewer.update_brush_cursor(self.brush_size)
