import sys
sys.path.append('../')
import numpy as np
import tifffile
from psdtags import PsdChannelId
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PySide6.QtGui import QImage, QPixmap, QPainter
from PySide6.QtCore import Qt, QRectF
from algorithms.multilayer import read_multilayer_tiff, write_multilayer_tiff_from_images


class ImageViewer(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_editor = None
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        self.zoom_factor = 1.0
        self.last_mouse_pos = None
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.brush_cursor = None
        self.setMouseTracking(True)
        self.space_pressed = False
        self.setDragMode(QGraphicsView.NoDrag)
        self.setCursor(Qt.BlankCursor)
        self.scrolling = False

    def set_image(self, qimage):
        pixmap = QPixmap.fromImage(qimage)
        self.pixmap_item.setPixmap(pixmap)
        self.setSceneRect(QRectF(pixmap.rect()))
        if self.zoom_factor == 1.0:
            self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
            self.zoom_factor = self.get_current_scale()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space and not self.scrolling:
            self.space_pressed = True
            self.setCursor(Qt.OpenHandCursor)
            if self.brush_cursor:
                self.brush_cursor.hide()
        elif event.key() == Qt.Key_X:
            self.image_editor.start_temp_view()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.space_pressed = False
            if not self.scrolling:
                self.setCursor(Qt.BlankCursor)
                if self.brush_cursor:
                    self.brush_cursor.show()
        elif event.key() == Qt.Key_X:
            self.image_editor.end_temp_view()
            return
        super().keyReleaseEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.space_pressed:
                self.scrolling = True
                self.last_mouse_pos = event.position()
                self.setCursor(Qt.ClosedHandCursor)
                if self.brush_cursor:
                    self.brush_cursor.hide()
            else:
                if self.brush_cursor:
                    self.brush_cursor.show()
        self.image_viewer.setFocus()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.scrolling:
            self.scrolling = False
            if self.space_pressed:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.BlankCursor)
                if self.brush_cursor:
                    self.brush_cursor.show()
            self.last_mouse_pos = None
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.position().toPoint())
        brush_size = self.image_editor.brush_size
        if self.brush_cursor:
            self.brush_cursor.setRect(
                scene_pos.x() - brush_size / 2,
                scene_pos.y() - brush_size / 2,
                brush_size, brush_size
            )
        else:
            self.brush_cursor = self.scene.addEllipse(
                scene_pos.x() - brush_size / 2,
                scene_pos.y() - brush_size / 2,
                brush_size, brush_size,
                QtGui.QPen(QtGui.QColor(255, 0, 0), 2),
                QtGui.QBrush(QtGui.QColor(255, 0, 0, 150))
            )
        if self.scrolling and event.buttons() & Qt.LeftButton:
            delta = event.position() - self.last_mouse_pos
            self.last_mouse_pos = event.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        else:
            super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor
        if event.angleDelta().y() > 0:
            self.scale(zoom_in_factor, zoom_in_factor)
            self.zoom_factor *= zoom_in_factor
        else:
            self.scale(zoom_out_factor, zoom_out_factor)
            self.zoom_factor *= zoom_out_factor
        if self.brush_cursor:
            mouse_pos = self.mapFromGlobal(QtGui.QCursor.pos())
            scene_pos = self.mapToScene(mouse_pos)
            brush_size = self.image_editor.brush_size
            self.brush_cursor.setRect(
                scene_pos.x() - brush_size / 2,
                scene_pos.y() - brush_size / 2,
                brush_size, brush_size
            )

    def update_brush_cursor(self, size):
        if self.brush_cursor:
            rect = self.brush_cursor.rect()
            center_x = rect.x() + rect.width() / 2
            center_y = rect.y() + rect.height() / 2
            self.brush_cursor.setRect(
                center_x - size / 2,
                center_y - size / 2,
                size, size
            )

    def leaveEvent(self, event):
        if self.brush_cursor:
            self.brush_cursor.hide()
        super().leaveEvent(event)

    def enterEvent(self, event):
        if self.brush_cursor:
            self.brush_cursor.show()
        super().enterEvent(event)

    def setup_shortcuts(self):
        zoom_in = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+="), self)
        zoom_in.activated.connect(self.zoom_in)
        zoom_in_alt = QtGui.QShortcut(QtGui.QKeySequence("Ctrl++"), self)
        zoom_in_alt.activated.connect(self.zoom_in)
        zoom_out = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+-"), self)
        zoom_out.activated.connect(self.zoom_out)
        reset_zoom = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+0"), self)
        reset_zoom.activated.connect(self.reset_zoom)

    def zoom_in(self):
        self.scale(1.25, 1.25)
        self.zoom_factor *= 1.25

    def zoom_out(self):
        self.scale(0.8, 0.8)
        self.zoom_factor *= 0.8

    def reset_zoom(self):
        self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
        self.zoom_factor = self.get_current_scale()

    def actual_size(self):
        self.resetTransform()
        self.zoom_factor = 1.0

    def get_current_scale(self):
        return self.transform().m11()

    def get_view_state(self):
        return {
            'zoom': self.zoom_factor,
            'h_scroll': self.horizontalScrollBar().value(),
            'v_scroll': self.verticalScrollBar().value()
        }

    def set_view_state(self, state):
        if state:
            self.resetTransform()
            self.scale(state['zoom'], state['zoom'])
            self.horizontalScrollBar().setValue(state['h_scroll'])
            self.verticalScrollBar().setValue(state['v_scroll'])
            self.zoom_factor = state['zoom']


class ImageEditor(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_stack = None
        self.master_layer = None
        self.current_layer = 0
        self.brush_size = 20
        self.view_mode = 'master'
        self.temp_view_individual = False
        self.setup_ui()
        self.setup_menu()
        self.setup_shortcuts()
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.KeyPress and event.key() == Qt.Key_X:
            self.start_temp_view()
            return True
        elif event.type() == QtCore.QEvent.KeyRelease and event.key() == Qt.Key_X:
            self.end_temp_view()
            return True
        return super().eventFilter(obj, event)

    def setup_shortcuts(self):
        zoom_in = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+="), self)
        zoom_in.activated.connect(self.image_viewer.zoom_in)
        zoom_in_alt = QtGui.QShortcut(QtGui.QKeySequence("Ctrl++"), self)
        zoom_in_alt.activated.connect(self.image_viewer.zoom_in)
        zoom_out = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+-"), self)
        zoom_out.activated.connect(self.image_viewer.zoom_out)
        reset_zoom = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+0"), self)
        reset_zoom.activated.connect(self.image_viewer.reset_zoom)
        prev_layer = QtGui.QShortcut(QtGui.QKeySequence(Qt.Key_Up), self, context=Qt.ApplicationShortcut)
        prev_layer.activated.connect(self.prev_layer)
        next_layer = QtGui.QShortcut(QtGui.QKeySequence(Qt.Key_Down), self, context=Qt.ApplicationShortcut)
        next_layer.activated.connect(self.next_layer)

    def setup_ui(self):
        self.setWindowTitle("Focus Stack Editor")
        self.resize(1400, 900)
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QHBoxLayout(central_widget)
        self.image_viewer = ImageViewer()
        self.image_viewer.image_editor = self
        self.image_viewer.setFocusPolicy(Qt.StrongFocus)
        side_panel = QtWidgets.QWidget()
        side_layout = QtWidgets.QVBoxLayout(side_panel)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(5)
        brush_panel = QtWidgets.QFrame()
        brush_panel.setFrameShape(QtWidgets.QFrame.StyledPanel)
        brush_layout = QtWidgets.QVBoxLayout(brush_panel)
        brush_layout.setContentsMargins(5, 5, 5, 5)
        brush_label = QtWidgets.QLabel("Brush Size")
        brush_label.setAlignment(QtCore.Qt.AlignCenter)
        brush_layout.addWidget(brush_label)
        self.brush_size_slider = QtWidgets.QSlider(Qt.Horizontal)
        self.brush_size_slider.setRange(5, 100)
        self.brush_size_slider.setValue(self.brush_size)
        self.brush_size_slider.valueChanged.connect(self.update_brush_size)
        brush_layout.addWidget(self.brush_size_slider)
        self.brush_preview = QtWidgets.QLabel()
        self.brush_preview.setAlignment(QtCore.Qt.AlignCenter)
        self.brush_preview.setFixedSize(100, 100)
        self.update_brush_preview()
        brush_layout.addWidget(self.brush_preview)
        side_layout.addWidget(brush_panel)

        master_label = QtWidgets.QLabel("Master")
        master_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 11px;
                padding: 4px;
                color: #444;
                border-bottom: 1px solid #ddd;
                background: #f5f5f5;
            }
        """)
        master_label.setAlignment(QtCore.Qt.AlignCenter)
        master_label.setFixedHeight(24)
        side_layout.addWidget(master_label)
        self.master_thumbnail_frame = QtWidgets.QFrame()
        self.master_thumbnail_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        master_thumbnail_layout = QtWidgets.QVBoxLayout(self.master_thumbnail_frame)
        master_thumbnail_layout.setContentsMargins(5, 5, 5, 5)
        self.master_thumbnail_label = QtWidgets.QLabel()
        self.master_thumbnail_label.setAlignment(QtCore.Qt.AlignCenter)
        self.master_thumbnail_label.setFixedSize(100, 100)
        self.master_thumbnail_label.mousePressEvent = lambda e: self.set_view_master()
        master_thumbnail_layout.addWidget(self.master_thumbnail_label)
        side_layout.addWidget(self.master_thumbnail_frame)
        side_layout.addSpacing(10)
        layers_label = QtWidgets.QLabel("Layers")
        layers_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 11px;
                padding: 4px;
                color: #444;
                border-bottom: 1px solid #ddd;
                background: #f5f5f5;
            }
        """)
        layers_label.setAlignment(QtCore.Qt.AlignCenter)
        layers_label.setFixedHeight(24)
        side_layout.addWidget(layers_label)
        self.thumbnail_list = QtWidgets.QListWidget()
        self.thumbnail_list.setFocusPolicy(Qt.StrongFocus)
        self.thumbnail_list.setViewMode(QtWidgets.QListWidget.IconMode)
        self.thumbnail_list.setIconSize(QtCore.QSize(100, 100))
        self.thumbnail_list.setResizeMode(QtWidgets.QListWidget.Adjust)
        self.thumbnail_list.setFlow(QtWidgets.QListWidget.TopToBottom)
        self.thumbnail_list.setMovement(QtWidgets.QListWidget.Static)
        self.thumbnail_list.setFixedWidth(120)
        self.thumbnail_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.thumbnail_list.itemClicked.connect(self.change_layer_item)
        side_layout.addWidget(self.thumbnail_list, 1)
        control_panel = QtWidgets.QWidget()
#        control_layout = QtWidgets.QVBoxLayout(control_panel)
        layout.addWidget(self.image_viewer, 1)
        layout.addWidget(side_panel, 0)
        layout.addWidget(control_panel, 0)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(5)

    def setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        file_menu.addAction("Open...", self.open_file, "Ctrl+O")
        file_menu.addAction("Save", self.save_file, "Ctrl+S")
        view_menu = menubar.addMenu("View")
        zoom_in_action = QtGui.QAction("Zoom In", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self.image_viewer.zoom_in)
        view_menu.addAction(zoom_in_action)
        zoom_out_action = QtGui.QAction("Zoom Out", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self.image_viewer.zoom_out)
        view_menu.addAction(zoom_out_action)
        adapt_action = QtGui.QAction("Adapt to Screen", self)
        adapt_action.setShortcut("Ctrl+0")
        adapt_action.triggered.connect(self.image_viewer.reset_zoom)
        view_menu.addAction(adapt_action)
        view_menu.addSeparator()
        actual_size_action = QtGui.QAction("Actual Size", self)
        actual_size_action.triggered.connect(self.image_viewer.actual_size)
        view_menu.addAction(actual_size_action)
        view_menu.addSeparator()
        view_master_action = QtGui.QAction("View Master", self)
        view_master_action.setShortcut("M")
        view_master_action.triggered.connect(self.set_view_master)
        view_menu.addAction(view_master_action)
        view_individual_action = QtGui.QAction("View Individual", self)
        view_individual_action.setShortcut("L")
        view_individual_action.triggered.connect(self.set_view_individual)
        view_menu.addAction(view_individual_action)
        view_menu.addSeparator()

    def load_tiff_stack(self, path):
        try:
            print(f"Loading file: {path}")
            psd_data = read_multilayer_tiff(path)
            layers = []
            for layer in psd_data.layers.layers:
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
            if layers:
                print(f"Found {len(layers)} layers")
                return np.array(layers), None
        except Exception as e:
            print(f"Error loading PSD data: {str(e)}")
            try:
                stack = tifffile.imread(path)
                if stack.ndim == 3:
                    return stack, None
                return None, None
            except Exception as e:
                print(f"Error loading TIFF: {str(e)}")
                return None, None

    def open_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Image", "", "Images (*.tif *.tiff *.png *.jpg)")
        if path:
            self.current_stack, _ = self.load_tiff_stack(path)
            if self.current_stack is not None and len(self.current_stack) > 0:
                self.master_layer = self.current_stack[0].copy()
            self.update_thumbnails()
            self.change_layer(0)
            self.image_viewer.reset_zoom()
            self.statusBar().showMessage(f"Loaded: {path}")
            self.thumbnail_list.setFocus()

    def save_file(self):
        if not self.current_stack:
            return

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

    def update_thumbnails(self):
        if self.master_layer is not None:
            if self.master_layer.ndim == 3 and self.master_layer.shape[-1] == 3:
                master_thumbnail = self.create_rgb_thumbnail(self.master_layer)
            else:
                master_thumbnail = self.create_grayscale_thumbnail(self.master_layer)
        self.master_thumbnail_label.setPixmap(master_thumbnail)
        self.thumbnail_list.clear()
        if self.current_stack is None:
            return
        for i in range(len(self.current_stack)):
            layer = self.current_stack[i]
            if layer.ndim == 3 and layer.shape[-1] == 3:
                thumbnail = self.create_rgb_thumbnail(layer)
            else:
                thumbnail = self.create_grayscale_thumbnail(layer)
            item = QtWidgets.QListWidgetItem(f"Layer {i + 1}")
            item.setIcon(QtGui.QIcon(thumbnail))
            self.thumbnail_list.addItem(item)

    def create_rgb_thumbnail(self, layer):
        if layer.dtype == np.uint16:
            layer = (layer // 256).astype(np.uint8)
        height, width, _ = layer.shape
        qimg = QtGui.QImage(layer.data, width, height, 3 * width, QtGui.QImage.Format_RGB888)
        return QtGui.QPixmap.fromImage(qimg.scaled(100, 100, QtCore.Qt.KeepAspectRatio))

    def create_grayscale_thumbnail(self, layer):
        if layer.dtype == np.uint16:
            p2, p98 = np.percentile(layer, (2, 98))
            layer = np.clip((layer - p2) * 255.0 / (p98 - p2), 0, 255).astype(np.uint8)
        height, width = layer.shape
        qimg = QtGui.QImage(layer.data, width, height, width, QtGui.QImage.Format_Grayscale8)
        return QtGui.QPixmap.fromImage(qimg.scaled(100, 100, QtCore.Qt.KeepAspectRatio))

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
            array = (array / 256).astype(np.uint8)
        if array.ndim == 2:
            height, width = array.shape
            bytes_per_line = width
            return QImage(array.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
        elif array.ndim == 3:
            height, width, _ = array.shape
            bytes_per_line = 3 * width
            return QImage(array.data, width, height, bytes_per_line, QImage.Format_RGB888)
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
        self.thumbnail_list.scrollToItem(
            self.thumbnail_list.item(index),
            QtWidgets.QAbstractItemView.PositionAtCenter
        )

    def update_brush_size(self, size):
        self.brush_size = size
        self.update_brush_preview()
        self.image_viewer.update_brush_cursor(size)

    def update_brush_preview(self):
        pixmap = QtGui.QPixmap(100, 100)
        pixmap.fill(Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtGui.QPen(Qt.red, 1))
        painter.setBrush(QtGui.QBrush(Qt.red))
        center = QtCore.QPoint(50, 50)
        painter.drawEllipse(center, self.brush_size // 2, self.brush_size // 2)
        painter.end()
        self.brush_preview.setPixmap(pixmap)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    editor = ImageEditor()
    editor.show()
    sys.exit(app.exec())
