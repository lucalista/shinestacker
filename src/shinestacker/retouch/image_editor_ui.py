# pylint: disable=C0114, C0115, C0116, E0611, R0902, R0914, R0915, R0904, W0108, R0911, R0903, W0718
import os
import traceback
from functools import partial
from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QKeySequence, QAction, QActionGroup, QGuiApplication
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QMenu,
                               QListWidget, QSlider, QMainWindow, QMessageBox, QDialog)
from .. config.constants import constants
from .. config.app_config import AppConfig
from .. config.gui_constants import gui_constants
from .. gui.recent_file_manager import RecentFileManager
from .. algorithms.exif import get_exif
from .. algorithms.utils import EXTENSIONS_GUI_STR_IN
from .image_viewer import ImageViewer
from .shortcuts_help import ShortcutsHelp
from .brush import Brush
from .brush_tool import BrushTool
from .layer_collection import LayerCollectionHandler
from .paint_area_manager import PaintAreaManager
from .undo_manager import UndoManager
from .layer_collection import LayerCollection
from .io_gui_handler import IOGuiHandler
from .display_manager import DisplayManager
from .filter_manager import FilterManager
from .denoise_filter import DenoiseFilter
from .unsharp_mask_filter import UnsharpMaskFilter
from .white_balance_filter import WhiteBalanceFilter
from .vignetting_filter import VignettingFilter
from .adjustments import LumiContrastFilter, SaturationVibranceFilter
from .local_tonemapping_filter import LocalTonemappingFilter
from .transformation_manager import TransfromationManager
from .exif_data import ExifData
from .reset_slider import ResetSlider


class ImageEditorUI(QMainWindow, LayerCollectionHandler):
    def __init__(self):
        QMainWindow.__init__(self)
        LayerCollectionHandler.__init__(self, LayerCollection())
        self._recent_file_manager = RecentFileManager("shinestacker-recent-images-files.txt")
        self.io_gui_handler = None
        self.brush = Brush()
        self.brush_tool = BrushTool()
        self.modified = False
        self.transformation_manager = TransfromationManager(self)
        self.paint_area_manager = PaintAreaManager()
        self.undo_manager = UndoManager(self.transformation_manager, self.paint_area_manager)
        self.undo_action = None
        self.redo_action = None
        self.undo_manager.stack_changed.connect(self.update_undo_redo_actions)
        self.shortcuts_help_dialog = None
        self.update_title()
        self.resize(1400, 900)
        center = QGuiApplication.primaryScreen().geometry().center()
        self.move(center - self.rect().center())
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        self.image_viewer = ImageViewer(
            self.layer_collection, self.brush_tool, self.paint_area_manager)
        self.image_viewer.connect_signals(
            self.handle_temp_view,
            self.end_copy_brush_area,
            self.handle_brush_size_change,
            self.handle_brush_hardness_change,
            self.handle_brush_opacity_change,
            self.handle_brush_flow_change,
            self.handle_needs_update)
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

        self.size_label = QLabel("Size")
        self.size_label.setAlignment(Qt.AlignLeft)
        brush_layout.addWidget(self.size_label)
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(0, gui_constants.BRUSH_SIZE_SLIDER_MAX)

        def brush_size_to_slider(size):
            if size <= gui_constants.BRUSH_SIZES['min']:
                return 0
            if size >= gui_constants.BRUSH_SIZES['max']:
                return gui_constants.BRUSH_SIZE_SLIDER_MAX
            normalized = ((size - gui_constants.BRUSH_SIZES['min']) /
                          gui_constants.BRUSH_SIZES['max']) ** (1 / gui_constants.BRUSH_GAMMA)
            return int(normalized * gui_constants.BRUSH_SIZE_SLIDER_MAX)

        self.size_slider.setValue(brush_size_to_slider(self.brush.size))
        brush_layout.addWidget(self.size_slider)

        self.hardness_label = QLabel("Hardness")
        self.hardness_label.setAlignment(Qt.AlignLeft)
        brush_layout.addWidget(self.hardness_label)
        self.hardness_slider = QSlider(Qt.Horizontal)
        self.hardness_slider.setRange(0, 100)
        self.hardness_slider.setValue(self.brush.hardness)
        brush_layout.addWidget(self.hardness_slider)

        self.opacity_label = QLabel("Opacity")
        self.opacity_label.setAlignment(Qt.AlignLeft)
        brush_layout.addWidget(self.opacity_label)
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(self.brush.opacity)
        brush_layout.addWidget(self.opacity_slider)

        self.flow_label = QLabel("Flow")
        self.flow_label.setAlignment(Qt.AlignLeft)
        brush_layout.addWidget(self.flow_label)
        self.flow_slider = QSlider(Qt.Horizontal)
        self.flow_slider.setRange(1, 100)
        self.flow_slider.setValue(self.brush.flow)
        brush_layout.addWidget(self.flow_slider)

        self.luminosity_label = QLabel("Luminosity")
        self.luminosity_label.setAlignment(Qt.AlignLeft)
        brush_layout.addWidget(self.luminosity_label)
        self.luminosity_slider = ResetSlider(0, Qt.Horizontal)
        self.luminosity_slider.setRange(-30, +30)
        self.luminosity_slider.setValue(0)
        brush_layout.addWidget(self.luminosity_slider)

        side_layout.addWidget(brush_panel)
        self.brush_preview_widget = QLabel()
        self.brush_preview_widget.setContentsMargins(0, 0, 0, 0)
        self.brush_preview_widget.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 0px;
                margin: 0px;
            }
        """)
        self.brush_preview_widget.setAlignment(Qt.AlignCenter)
        self.brush_preview_widget.setFixedHeight(100)
        brush_layout.addWidget(self.brush_preview_widget)
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
            f"#thumbnailContainer{{ border: 2px solid {gui_constants.THUMB_MASTER_HI_COLOR}; }}")
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
        self.exif_dialog = None

        def change_layer_item(item):
            layer_idx = self.thumbnail_list.row(item)
            self.change_layer(layer_idx)
            self.display_manager.highlight_thumbnail(layer_idx)

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
        self.filter_manager = FilterManager(self)
        self.io_gui_handler = IOGuiHandler(self.layer_collection, self.undo_manager, parent=self)
        self.display_manager.status_message_requested.connect(
            lambda msg: self.show_status_message(msg, 4000))
        self.io_gui_handler.status_message_requested.connect(
            lambda msg: self.show_status_message(msg, 4000))
        self.io_gui_handler.update_title_requested.connect(self.update_title)
        self.io_gui_handler.mark_as_modified_requested.connect(self.mark_as_modified)
        self.io_gui_handler.change_layer_requested.connect(self.change_layer)
        self.io_gui_handler.add_recent_file_requested.connect(self.add_recent_file)
        self.io_gui_handler.set_enabled_file_open_close_actions_requested.connect(
            self.set_enabled_file_open_close_actions)
        self.brush_tool.setup_ui(self.brush, self.brush_preview_widget, self.image_viewer,
                                 self.size_slider, self.hardness_slider, self.opacity_slider,
                                 self.flow_slider, self.luminosity_slider)

        self.size_slider.valueChanged.connect(self.update_brush_size)
        self.hardness_slider.valueChanged.connect(self.update_brush_hardness)
        self.opacity_slider.valueChanged.connect(self.update_brush_opacity)
        self.flow_slider.valueChanged.connect(self.update_brush_flow)
        self.luminosity_slider.valueChanged.connect(self.update_brush_luminosity)
        self.update_brush_size(self.size_slider.value())
        self.update_brush_hardness(self.hardness_slider.value())
        self.update_brush_opacity(self.opacity_slider.value())
        self.update_brush_flow(self.flow_slider.value())
        self.update_brush_luminosity(self.luminosity_slider.value())

        self.image_viewer.set_brush(self.brush_tool.brush)
        self.image_viewer.set_preview_brush(self.brush_tool.brush)
        self.image_viewer.status.set_zoom_factor_requested.connect(self.handle_set_zoom_factor)
        self.brush_tool.update_brush_thumb()
        self.io_gui_handler.setup_ui(self.display_manager, self.image_viewer)
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        file_menu.addAction("&Open...", self.io_gui_handler.open_file, "Ctrl+O")
        self.recent_files_menu = QMenu("Open &Recent", file_menu)
        file_menu.addMenu(self.recent_files_menu)
        self.update_recent_files()
        self.save_action = QAction("&Save", self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self.io_gui_handler.save_file)
        file_menu.addAction(self.save_action)
        self.save_as_action = QAction("Save &As...", self)
        self.save_as_action.setShortcut("Ctrl+Shift+S")
        self.save_as_action.triggered.connect(self.io_gui_handler.save_file_as)
        file_menu.addAction(self.save_as_action)

        self.save_actions_set_enabled(False)

        file_menu.addAction("&Close", self.close_file, "Ctrl+W")
        file_menu.addSeparator()
        show_exif_action = QAction("Show EXIF Data", self)
        show_exif_action.triggered.connect(self.show_exif_data)
        show_exif_action.setProperty("requires_file", True)
        file_menu.addAction(show_exif_action)
        delete_exif_action = QAction("Delete EXIF Data", self)
        delete_exif_action.triggered.connect(self.delete_exif_data)
        delete_exif_action.setProperty("requires_file", True)
        file_menu.addAction(delete_exif_action)
        file_menu.addSeparator()
        file_menu.addAction("&Import Frames", self.io_gui_handler.import_frames)
        file_menu.addAction("Import &EXIF Data", self.select_exif_path)

        edit_menu = menubar.addMenu("&Edit")
        self.undo_action = QAction("Undo", self)
        self.undo_action.setEnabled(False)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.triggered.connect(self.undo)
        edit_menu.addAction(self.undo_action)
        self.redo_action = QAction("Redo", self)
        self.redo_action.setEnabled(False)
        self.redo_action.setShortcuts([QKeySequence("Ctrl+Shift+Z"), QKeySequence("Ctrl+Y")])
        self.redo_action.triggered.connect(self.redo)
        edit_menu.addAction(self.redo_action)
        edit_menu.addSeparator()

        transf_menu = QMenu("&Transform")
        rotate_90_cw_action = QAction(gui_constants.ROTATE_90_CW_LABEL, self)
        rotate_90_cw_action.setProperty("requires_file", True)
        rotate_90_cw_action.triggered.connect(lambda: self.transformation_manager.rotate_90_cw())
        transf_menu.addAction(rotate_90_cw_action)
        rotate_90_ccw_action = QAction(gui_constants.ROTATE_90_CCW_LABEL, self)
        rotate_90_ccw_action.setProperty("requires_file", True)
        rotate_90_ccw_action.triggered.connect(lambda: self.transformation_manager.rotate_90_ccw())
        transf_menu.addAction(rotate_90_ccw_action)
        rotate_180_action = QAction(gui_constants.ROTATE_180_LABEL, self)
        rotate_180_action.triggered.connect(lambda: self.transformation_manager.rotate_180())
        rotate_180_action.setProperty("requires_file", True)
        transf_menu.addAction(rotate_180_action)
        edit_menu.addMenu(transf_menu)

        adjust_menu = QMenu("&Adjust")
        luminosity_action = QAction("Luminosity, Contrast", self)
        luminosity_action.setProperty("requires_file", True)
        luminosity_action.triggered.connect(self.luminosity_filter)
        adjust_menu.addAction(luminosity_action)
        saturation_action = QAction("Saturation, Vibrance", self)
        saturation_action.setProperty("requires_file", True)
        saturation_action.triggered.connect(self.saturation_filter)
        adjust_menu.addAction(saturation_action)
        white_balance_action = QAction("White Balance", self)
        white_balance_action.setProperty("requires_file", True)
        white_balance_action.triggered.connect(self.white_balance)
        adjust_menu.addAction(white_balance_action)
        edit_menu.addMenu(adjust_menu)

        edit_menu.addSeparator()

        copy_current_to_master_action = QAction("Copy Current Layer to Master", self)
        copy_current_to_master_action.setShortcut("Ctrl+M")
        copy_current_to_master_action.setProperty("requires_file", True)
        copy_current_to_master_action.triggered.connect(self.copy_layer_to_master)
        edit_menu.addAction(copy_current_to_master_action)

        view_menu = menubar.addMenu("&View")

        fullscreen_action = QAction("Full Screen", self)
        fullscreen_action.setShortcuts([QKeySequence("Ctrl+Meta+F"), QKeySequence("F11")])
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        fullscreen_action.setCheckable(True)
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)

        view_menu.addSeparator()

        self.view_strategy_menu = QMenu("View &Mode", view_menu)

        self.view_mode_actions = {
            'overlaid': QAction("Overlaid", self),
            'sidebyside': QAction("Side by Side", self),
            'topbottom': QAction("Top-Bottom", self)
        }
        overlaid_mode = self.view_mode_actions['overlaid']
        overlaid_mode.setShortcut("Ctrl+1")
        overlaid_mode.setCheckable(True)
        overlaid_mode.triggered.connect(lambda: self.set_strategy('overlaid'))
        self.view_strategy_menu.addAction(overlaid_mode)
        side_by_side_mode = self.view_mode_actions['sidebyside']
        side_by_side_mode.setShortcut("Ctrl+2")
        side_by_side_mode.setCheckable(True)
        side_by_side_mode.triggered.connect(lambda: self.set_strategy('sidebyside'))
        self.view_strategy_menu.addAction(side_by_side_mode)
        side_by_side_mode = self.view_mode_actions['topbottom']
        side_by_side_mode.setShortcut("Ctrl+3")
        side_by_side_mode.setCheckable(True)
        side_by_side_mode.triggered.connect(lambda: self.set_strategy('topbottom'))
        self.view_strategy_menu.addAction(side_by_side_mode)
        view_menu.addMenu(self.view_strategy_menu)

        filter_handles = (
            self.display_manager.update_master_thumbnail,
            self.mark_as_modified,
            self.view_strategy_menu.setEnabled
        )
        self.filter_manager.register_filter(
            "Luminosity, Contrast", LumiContrastFilter, *filter_handles)
        self.filter_manager.register_filter(
            "Saturation, Vibrance", SaturationVibranceFilter, *filter_handles)
        self.filter_manager.register_filter(
            "Denoise", DenoiseFilter, *filter_handles)
        self.filter_manager.register_filter(
            "Unsharp Mask", UnsharpMaskFilter, *filter_handles)
        self.filter_manager.register_filter(
            "Local Tonemapping", LocalTonemappingFilter, *filter_handles)
        self.filter_manager.register_filter(
            "White Balance", WhiteBalanceFilter, *filter_handles)
        self.filter_manager.register_filter(
            "Vignetting Correction", VignettingFilter, *filter_handles)

        cursor_menu = view_menu.addMenu("Cursor Style")

        self.cursor_style_actions = {
            'brush': QAction("Simple Brush", self),
            'preview': QAction("Brush Preview", self),
            'outline': QAction("Outline Only", self)
        }
        brush_action = self.cursor_style_actions['brush']
        brush_action.setCheckable(True)
        brush_action.setProperty("requires_file", True)
        brush_action.triggered.connect(lambda: set_cursor_style('brush'))
        cursor_menu.addAction(brush_action)

        preview_action = self.cursor_style_actions['preview']
        preview_action.setProperty("requires_file", True)
        preview_action.setCheckable(True)
        preview_action.triggered.connect(lambda: set_cursor_style('preview'))
        cursor_menu.addAction(preview_action)

        outline_action = self.cursor_style_actions['outline']
        outline_action.setProperty("requires_file", True)
        outline_action.setCheckable(True)
        outline_action.triggered.connect(lambda: set_cursor_style('outline'))
        cursor_menu.addAction(outline_action)

        def set_cursor_style(cursor_style):
            self.image_viewer.set_cursor_style(cursor_style)
            for label, style in self.cursor_style_actions.items():
                style.setEnabled(label != cursor_style)
                style.setChecked(label == cursor_style)

        set_cursor_style(self.image_viewer.get_cursor_style())

        cursor_group = QActionGroup(self)
        cursor_group.addAction(preview_action)
        cursor_group.addAction(outline_action)
        cursor_group.addAction(brush_action)
        cursor_group.setExclusive(True)

        view_menu.addSeparator()

        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setShortcuts([QKeySequence("Ctrl++"), QKeySequence("+"),
                                     QKeySequence("Ctrl+="), QKeySequence("=")])
        zoom_in_action.setProperty("requires_file", True)
        zoom_in_action.triggered.connect(self.image_viewer.zoom_in)
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setShortcuts([QKeySequence("Ctrl+-"), QKeySequence("-")])
        zoom_out_action.setProperty("requires_file", True)
        zoom_out_action.triggered.connect(self.image_viewer.zoom_out)
        view_menu.addAction(zoom_out_action)

        adapt_action = QAction("Adapt to Screen", self)
        adapt_action.setShortcut("Ctrl+0")
        adapt_action.setProperty("requires_file", True)
        adapt_action.triggered.connect(self.image_viewer.reset_zoom)
        view_menu.addAction(adapt_action)

        actual_size_action = QAction("Actual Size", self)
        actual_size_action.setShortcut("Ctrl+R")
        actual_size_action.setProperty("requires_file", True)
        actual_size_action.triggered.connect(self.image_viewer.actual_size)
        view_menu.addAction(actual_size_action)
        view_menu.addSeparator()

        self.view_master_action = QAction("View Master", self)
        self.view_master_action.setShortcut("M")
        self.view_master_action.setProperty("requires_file", True)
        self.view_master_action.triggered.connect(self.set_view_master)
        view_menu.addAction(self.view_master_action)

        self.view_individual_action = QAction("View Individual", self)
        self.view_individual_action.setShortcut("L")
        self.view_individual_action.setProperty("requires_file", True)
        self.view_individual_action.triggered.connect(self.set_view_individual)
        view_menu.addAction(self.view_individual_action)

        self.toggle_view_master_individual_action = QAction("Toggle Master/Individual", self)
        self.toggle_view_master_individual_action.setShortcut("T")
        self.toggle_view_master_individual_action.setProperty("requires_file", True)
        self.toggle_view_master_individual_action.triggered.connect(
            self.toggle_view_master_individual)
        view_menu.addAction(self.toggle_view_master_individual_action)
        view_menu.addSeparator()

        self.set_strategy(AppConfig.get('retouch_view_strategy'))

        sort_asc_action = QAction("Sort Layers A-Z", self)
        sort_asc_action.setProperty("requires_file", True)
        sort_asc_action.triggered.connect(lambda: self.sort_layers_ui('asc'))
        view_menu.addAction(sort_asc_action)

        sort_desc_action = QAction("Sort Layers Z-A", self)
        sort_desc_action.setProperty("requires_file", True)
        sort_desc_action.triggered.connect(lambda: self.sort_layers_ui('desc'))
        view_menu.addAction(sort_desc_action)

        view_menu.addSeparator()

        filter_menu = menubar.addMenu("&Filter")
        filter_menu.setObjectName("Filter")
        denoise_action = QAction("Denoise", self)
        denoise_action.setProperty("requires_file", True)
        denoise_action.triggered.connect(self.denoise_filter)
        filter_menu.addAction(denoise_action)
        unsharp_mask_action = QAction("Unsharp Mask", self)
        unsharp_mask_action.setProperty("requires_file", True)
        unsharp_mask_action.triggered.connect(self.unsharp_mask)
        filter_menu.addAction(unsharp_mask_action)

        local_tonemapping_action = QAction("Local Tonemapping", self)
        local_tonemapping_action.setProperty("requires_file", True)
        local_tonemapping_action.triggered.connect(self.local_tonemapping)
        filter_menu.addAction(local_tonemapping_action)

        vignetting_action = QAction("Vignetting Correction", self)
        vignetting_action.setProperty("requires_file", True)
        vignetting_action.triggered.connect(self.vignetting_correction)
        filter_menu.addAction(vignetting_action)

        help_menu = menubar.addMenu("&Help")
        help_menu.setObjectName("Help")
        shortcuts_help_action = QAction("Shortcuts and Mouse", self)

        self.zoom_factor_label = QLabel("")
        self.statusBar().addPermanentWidget(self.zoom_factor_label)
        self.statusBar().showMessage("Shine Stacker ready.", 4000)

        def shortcuts_help():
            self.shortcuts_help_dialog = ShortcutsHelp(self)
            self.shortcuts_help_dialog.exec()

        shortcuts_help_action.triggered.connect(shortcuts_help)
        help_menu.addAction(shortcuts_help_action)

        prev_layer = QShortcut(QKeySequence(Qt.Key_Up), self, context=Qt.ApplicationShortcut)
        prev_layer.activated.connect(self.prev_layer)
        next_layer = QShortcut(QKeySequence(Qt.Key_Down), self, context=Qt.ApplicationShortcut)
        next_layer.activated.connect(self.next_layer)

        self.set_enabled_file_open_close_actions(False)
        self.installEventFilter(self)

    def handle_config(self):
        self.set_strategy(AppConfig.get('retouch_view_strategy'))
        self.display_manager.update_timer.setInterval(AppConfig.get('display_refresh_time'))

    def set_enabled_view_toggles(self, enabled):
        self.view_master_action.setEnabled(enabled)
        self.view_individual_action.setEnabled(enabled)
        self.toggle_view_master_individual_action.setEnabled(enabled)

    def set_strategy(self, strategy):
        self.image_viewer.set_strategy(strategy)
        self.display_manager.view_mode = 'master'
        self.highlight_master_thumbnail(gui_constants.THUMB_MASTER_HI_COLOR)
        self.set_enabled_view_toggles(strategy == 'overlaid')
        for label, mode in self.view_mode_actions.items():
            mode.setEnabled(label != strategy)
            mode.setChecked(label == strategy)

    def set_enabled_file_open_close_actions(self, enabled):
        for action in self.findChildren(QAction):
            if action.property("requires_file"):
                action.setEnabled(enabled)

    def update_title(self):
        title = constants.APP_TITLE
        if self.io_gui_handler is not None:
            path = self.io_gui_handler.current_file_path()
            if path != '':
                title += f" - {path.split('/')[-1]}"
                if self.modified:
                    title += " *"
        self.window().setWindowTitle(title)

    def update_recent_files(self):
        self.recent_files_menu.clear()
        recent_files = self._recent_file_manager.get_files_with_display_names()
        for file_path, display_name in recent_files.items():
            action = self.recent_files_menu.addAction(display_name)
            action.setData(file_path)
            action.triggered.connect(partial(self.io_gui_handler.open_file, file_path))
        self.recent_files_menu.setEnabled(len(recent_files) > 0)

    def add_recent_file(self, file_path):
        self._recent_file_manager.add_file(file_path)
        self.update_recent_files()

    def show_status_message(self, message, timeout=0):
        self.statusBar().showMessage(message, timeout)

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
        if self.image_viewer.empty():
            return
        text = event.text()
        if text == '[':
            self.decrease_brush_size()
            return
        if text == ']':
            self.increase_brush_size()
            return
        if text == '{':
            self.decrease_brush_hardness()
            return
        if text == '}':
            self.increase_brush_hardness()
            return
        if text == ',':
            self.decrease_brush_opacity()
            return
        if text == '.':
            self.increase_brush_opacity()
            return
        if text == ';':
            self.decrease_brush_flow()
            return
        if text == ':':
            self.increase_brush_flow()
            return
        if text == '<':
            self.decrease_brush_luminosity()
            return
        if text == '>':
            self.increase_brush_luminosity()
            return
        super().keyPressEvent(event)
    # pylint: enable=C0103

    def increase_brush_size(self, amount=5):
        val = min(self.size_slider.value() + amount, self.size_slider.maximum())
        self.size_slider.setValue(val)
        self.update_brush_size(val)

    def decrease_brush_size(self, amount=5):
        val = max(self.size_slider.value() - amount, self.size_slider.minimum())
        self.size_slider.setValue(val)
        self.update_brush_size(val)

    def increase_brush_hardness(self, amount=2):
        val = min(self.hardness_slider.value() + amount, self.hardness_slider.maximum())
        self.hardness_slider.setValue(val)
        self.update_brush_hardness(val)

    def decrease_brush_hardness(self, amount=2):
        val = max(self.hardness_slider.value() - amount, self.hardness_slider.minimum())
        self.hardness_slider.setValue(val)
        self.update_brush_hardness(val)

    def increase_brush_opacity(self, amount=2):
        val = min(self.opacity_slider.value() + amount, self.opacity_slider.maximum())
        self.opacity_slider.setValue(val)
        self.update_brush_opacity(val)

    def decrease_brush_opacity(self, amount=2):
        val = max(self.opacity_slider.value() - amount, self.opacity_slider.minimum())
        self.opacity_slider.setValue(val)
        self.update_brush_opacity(val)

    def increase_brush_flow(self, amount=2):
        val = min(self.flow_slider.value() + amount, self.flow_slider.maximum())
        self.flow_slider.setValue(val)
        self.update_brush_flow(val)

    def decrease_brush_flow(self, amount=2):
        val = max(self.flow_slider.value() - amount, self.flow_slider.minimum())
        self.flow_slider.setValue(val)
        self.update_brush_flow(val)

    def increase_brush_luminosity(self, amount=1):
        val = min(self.luminosity_slider.value() + amount, self.luminosity_slider.maximum())
        self.luminosity_slider.setValue(val)
        self.update_brush_luminosity(val)

    def decrease_brush_luminosity(self, amount=1):
        val = min(self.luminosity_slider.value() - amount, self.luminosity_slider.maximum())
        self.luminosity_slider.setValue(val)
        self.update_brush_luminosity(val)

    def update_brush_size(self, slider_val):

        def slider_to_brush_size(slider_val):
            normalized = slider_val / gui_constants.BRUSH_SIZE_SLIDER_MAX
            size = gui_constants.BRUSH_SIZES['min'] + \
                gui_constants.BRUSH_SIZES['max'] * (normalized ** gui_constants.BRUSH_GAMMA)
            return max(gui_constants.BRUSH_SIZES['min'],
                       min(gui_constants.BRUSH_SIZES['max'], size))

        self.brush.size = slider_to_brush_size(slider_val)
        self.size_label.setText(f"Size: {int(self.brush.size)}px")
        self.brush_tool.update_brush_thumb()

    def update_brush_hardness(self, hardness):
        self.brush.hardness = hardness
        self.hardness_label.setText(f"Hardness: {self.brush.hardness}%")
        self.brush_tool.update_brush_thumb()

    def update_brush_opacity(self, opacity):
        self.brush.opacity = opacity
        self.opacity_label.setText(f"Opacity: {self.brush.opacity}%")
        self.brush_tool.update_brush_thumb()

    def update_brush_flow(self, flow):
        self.brush.flow = flow
        self.flow_label.setText(f"Flow: {self.brush.flow}%")
        self.brush_tool.update_brush_thumb()

    def update_brush_luminosity(self, luminosity):
        self.brush.luminosity = luminosity
        self.luminosity_label.setText(f"Luminosity: {self.brush.luminosity}%")
        self.brush_tool.update_brush_thumb()

    def sort_layers_ui(self, order):
        self.sort_layers(order)
        self.display_manager.update_thumbnails()
        self.change_layer(self.current_layer_idx())

    def change_layer(self, layer_idx):
        if 0 <= layer_idx < self.number_of_layers():
            self.set_current_layer_idx(layer_idx)
            self.display_manager.refresh_current_view()
            self.thumbnail_list.setCurrentRow(layer_idx)
            self.thumbnail_list.setFocus()
            self.image_viewer.update_brush_cursor()
            self.image_viewer.strategy.setFocus()

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
            self.display_manager.refresh_master_view()
            self.mark_as_modified()
            self.statusBar().showMessage(
                f"Copied layer {self.current_layer_idx() + 1} to master", 4000)

    def handle_needs_update(self):
        self.display_manager.needs_update = True
        if not self.display_manager.update_timer.isActive():
            self.display_manager.update_timer.start()
        self.mark_as_modified()

    def end_copy_brush_area(self):
        if self.display_manager.update_timer.isActive():
            self.display_manager.refresh_master_view()
            self.undo_manager.save_undo_state(self.master_layer_copy(), 'Brush Stroke')
            self.display_manager.update_timer.stop()
            self.mark_as_modified()

    def update_undo_redo_actions(self, has_undo, undo_desc, has_redo, redo_desc):
        self.image_viewer.update_brush_cursor()
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

    def select_exif_path(self):
        current_file_path = os.path.dirname(self.io_gui_handler.current_file_path_master)
        path, _ = self.io_gui_handler.file_dialog.open_file(
            "Select file with exif data",
            f"Images ({EXTENSIONS_GUI_STR_IN});;All Files (*)",
            current_file_path)
        if path:
            try:
                temp_exif_data = get_exif(path)
                self.exif_dialog = ExifData(temp_exif_data, "Import Selected EXIF Data",
                                            self.parent(), show_buttons=True)
                result = self.exif_dialog.exec()
                if result == QDialog.Accepted:
                    self.io_gui_handler.set_exif_data(temp_exif_data, path)
                    self.show_status_message(f"EXIF data loaded from {path}.")
                else:
                    self.show_status_message("EXIF data loading cancelled.")
                self.io_gui_handler.exif_err_msg = ''
            except Exception as e:
                traceback.print_stack()
                traceback.print_exc()
                self.io_gui_handler.exif_err_msg = "Can't read EXIF data from selected file " \
                    "due to the following error:\n\n" \
                    f"{str(e)}.\n\nEXIF data not loaded."
                QMessageBox.warning(self.parent(), "Warning", self.io_gui_handler.exif_err_msg)

    def show_exif_data(self):
        self.exif_dialog = ExifData(self.io_gui_handler.exif_data, "EXIF Data",
                                    self.parent(), show_buttons=False)
        self.exif_dialog.exec()

    def delete_exif_data(self):
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Warning: the current EXIF data will be erased.\n\nDo you want to continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.io_gui_handler.exif_data = None
            self.io_gui_handler.exif_path = ''

    def luminosity_filter(self):
        self.filter_manager.apply("Luminosity, Contrast")

    def saturation_filter(self):
        self.filter_manager.apply("Saturation, Vibrance")

    def denoise_filter(self):
        self.filter_manager.apply("Denoise")

    def unsharp_mask(self):
        self.filter_manager.apply("Unsharp Mask")

    def local_tonemapping(self):
        self.filter_manager.apply("Local Tonemapping")

    def white_balance(self, init_val=None):
        self.filter_manager.apply("White Balance", init_val=init_val or (128, 128, 128))

    def vignetting_correction(self):
        self.filter_manager.apply("Vignetting Correction")

    def highlight_master_thumbnail(self, color):
        self.master_thumbnail_frame.setStyleSheet(
            f"#thumbnailContainer{{ border: 2px solid {color}; }}")

    def save_actions_set_enabled(self, enabled):
        self.save_action.setEnabled(enabled)
        self.save_as_action.setEnabled(enabled)

    def close_file(self):
        if self.check_unsaved_changes():
            self.image_viewer.reset_zoom()
            self.io_gui_handler.close_file()
            self.set_master_layer(None)
            self.mark_as_modified(False)
            self.zoom_factor_label.setText("")

    def set_view_master(self):
        self.display_manager.set_view_master()
        self.highlight_master_thumbnail(gui_constants.THUMB_MASTER_HI_COLOR)

    def set_view_individual(self):
        self.display_manager.set_view_individual()
        self.highlight_master_thumbnail(gui_constants.THUMB_MASTER_LO_COLOR)

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
            return True
        return False

    def undo(self):
        if self.undo_manager.undo(self.master_layer()):
            self.display_manager.refresh_master_view()
            self.mark_as_modified()
            self.statusBar().showMessage("Undo applied", 4000)

    def redo(self):
        if self.undo_manager.redo(self.master_layer()):
            self.display_manager.refresh_master_view()
            self.mark_as_modified()
            self.statusBar().showMessage("Redo applied", 4000)

    def handle_temp_view(self, start):
        if start:
            self.display_manager.start_temp_view()
            self.highlight_master_thumbnail(gui_constants.THUMB_MASTER_LO_COLOR)
        else:
            self.display_manager.end_temp_view()
            self.highlight_master_thumbnail(gui_constants.THUMB_MASTER_HI_COLOR)

    def handle_brush_size_change(self, delta):
        if delta > 0:
            self.increase_brush_size()
        else:
            self.decrease_brush_size()

    def handle_brush_hardness_change(self, delta):
        if delta > 0:
            self.increase_brush_hardness()
        else:
            self.decrease_brush_hardness()

    def handle_brush_opacity_change(self, delta):
        if delta > 0:
            self.increase_brush_opacity()
        else:
            self.decrease_brush_opacity()

    def handle_brush_flow_change(self, delta):
        if delta > 0:
            self.increase_brush_flow()
        else:
            self.decrease_brush_flow()

    def handle_set_zoom_factor(self, zoom_factor):
        self.zoom_factor_label.setText(f"zoom: {zoom_factor:.1%}")
