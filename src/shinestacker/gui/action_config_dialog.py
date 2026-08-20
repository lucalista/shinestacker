# pylint: disable=C0114, C0115, C0116, E0611, R0913, R0917, R0915, R0912, R0902
# pylint: disable=E0606, W0718, R1702, W0102, W0221, R0914, C0302, R0903
import os
import traceback
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget, QLabel, QMessageBox, QStackedWidget, QSpinBox
from .. config.constants import constants
from .. config.app_config import AppConfig
from .. algorithms.utils import EXTENSIONS_SUPPORTED_IN
from .. algorithms.feature_match import validate_align_config
from . action_config import (
    DefaultActionConfigurator, add_tab, create_tab_layout, create_tab_widget,
    FIELD_TEXT, FIELD_ABS_PATH, FIELD_REL_PATH, FIELD_FLOAT,
    FIELD_INT, FIELD_INT_TUPLE, FIELD_BOOL, FIELD_COMBO, FIELD_REF_IDX
)
from .folder_file_selection import FolderFileSelectionWidget
from .config_dialog import ConfigDialog


class ActionConfigDialog(ConfigDialog):
    def __init__(self, action, current_wd, parent=None):
        self.action = action
        self.current_wd = current_wd
        super().__init__(f"Configure {action.type_name}", parent)

    def create_form_content(self):
        self.configurator = self.get_configurator(self.action.type_name)
        self.configurator.create_form(self.container_layout, self.action)

    def get_configurator(self, action_type):
        configurators = {
            constants.ACTION_JOB: JobConfigurator,
            constants.ACTION_COMBO: CombinedActionsConfigurator,
            constants.ACTION_NOISEDETECTION: NoiseDetectionConfigurator,
            constants.ACTION_FOCUSSTACK: FocusStackConfigurator,
            constants.ACTION_FOCUSSTACKBUNCH: FocusStackBunchConfigurator,
            constants.ACTION_MULTILAYER: MultiLayerConfigurator,
            constants.ACTION_MASKNOISE: MaskNoiseConfigurator,
            constants.ACTION_VIGNETTING: VignettingConfigurator,
            constants.ACTION_ALIGNFRAMES: AlignFramesConfigurator,
            constants.ACTION_BALANCEFRAMES: BalanceFramesConfigurator,
        }
        return configurators.get(
            action_type, DefaultActionConfigurator)(self.expert(), self.current_wd)

    def accept(self):
        if self.configurator.update_params(self.action.params):
            super().accept()

    def reset_to_defaults(self):
        builder = self.configurator.get_builder()
        if builder:
            builder.reset_to_defaults()

    def expert(self):
        return AppConfig.get('expert_options')


class JobConfigurator(DefaultActionConfigurator):
    def __init__(self, expert, current_wd):
        super().__init__(expert, current_wd, expert_toggle=False)
        self.working_path_label = None
        self.input_path_label = None
        self.frames_label = None
        self.input_widget = None

    def create_form(self, layout, action):
        super().create_form(layout, action, "Job")
        self.input_widget = FolderFileSelectionWidget(AppConfig.get('input_folder_path'))
        self.frames_label = QLabel("0")
        working_path = action.params.get('working_path', '')
        input_path = action.params.get('input_path', '')
        input_filepaths = action.params.get('input_filepaths', [])
        if isinstance(input_filepaths, str) and input_filepaths:
            input_filepaths = input_filepaths.split(constants.PATH_SEPARATOR)
        self.working_path_label = QLabel(working_path or "Not set")
        self.input_path_label = QLabel(input_path or "Not set")
        if input_filepaths:
            full_input_dir = os.path.normpath(os.path.join(working_path, input_path))
            self.input_widget.selected_files = [os.path.join(full_input_dir, f)
                                                for f in input_filepaths]
            self.input_widget.path_edit.setText(full_input_dir)
            self.input_widget.files_mode_radio.setChecked(True)
            self.input_widget.selection_mode = 'files'  # Explicitly set the mode
        else:
            full_input_dir = os.path.normpath(os.path.join(working_path, input_path))
            self.input_widget.path_edit.setText(full_input_dir)
            self.input_widget.folder_mode_radio.setChecked(True)
            self.input_widget.selection_mode = 'folder'  # Explicitly set the mode
        self.input_widget.text_changed_connect(self.update_paths_and_frames)
        self.input_widget.folder_mode_radio.toggled.connect(self.update_paths_and_frames)
        self.input_widget.files_mode_radio.toggled.connect(self.update_paths_and_frames)
        self.add_bold_label("Input Selection:")
        self.add_row(self.input_widget)
        self.add_labelled_row("Number of frames: ", self.frames_label)
        self.add_bold_label("Derived Paths:")
        self.add_labelled_row("Working path: ", self.working_path_label)
        self.add_labelled_row("Input path:", self.input_path_label)
        self.set_paths_and_frames(working_path, input_path, input_filepaths)

    def update_frames_count(self):
        if self.input_widget.get_selection_mode() == 'files':
            count = self.input_widget.num_selected_files()
        else:
            count = self.count_image_files(self.input_widget.get_path())
        self.frames_label.setText(str(count))

    def set_paths_and_frames(self, working_path, input_path, input_filepaths):
        self.input_path_label.setText(input_path or "Not set")
        self.working_path_label.setText(working_path or "Not set")
        self.frames_label.setText(str(len(input_filepaths)))

    def update_paths_and_frames(self):
        input_fullpath = self.input_widget.get_path()
        if input_fullpath:
            normalized_path = os.path.normpath(input_fullpath)
            working_path = os.path.dirname(normalized_path)
            input_path = os.path.basename(normalized_path)
        else:
            working_path = ""
            input_path = ""
        self.input_path_label.setText(input_path or "Not set")
        self.working_path_label.setText(working_path or "Not set")
        self.update_frames_count()

    def count_image_files(self, path):
        if not path or not os.path.isdir(path):
            return 0
        count = 0
        for filename in os.listdir(path):
            if os.path.splitext(filename)[-1][1:].lower() in EXTENSIONS_SUPPORTED_IN:
                count += 1
        return count

    def update_params(self, params):
        if not super().update_params(params):
            return False
        selection_mode = self.input_widget.get_selection_mode()
        selected_files = self.input_widget.get_selected_files()
        if selection_mode == 'files' and selected_files:
            input_full_path = os.path.dirname(selected_files[0])
            params['input_filepaths'] = self.input_widget.get_selected_filenames()
        else:
            input_full_path = self.input_widget.get_path()
            params['input_filepaths'] = []
        input_full_path = os.path.normpath(input_full_path) if input_full_path else ""
        if input_full_path:
            working_path = os.path.dirname(input_full_path)
            input_path = os.path.basename(input_full_path)
        else:
            working_path = ""
            input_path = ""
        if not working_path:
            QMessageBox.warning(
                None, "Error",
                "Please select a working directory. "
                "The working directory is the parent folder of your input selection."
            )
            self.input_widget.browse_button.setFocus()
            return False
        if not os.path.exists(working_path):
            QMessageBox.warning(
                None, "Error",
                f"Working directory '{working_path}' does not exist. "
                "Please select a valid directory."
            )
            self.input_widget.browse_button.setFocus()
            return False
        if selection_mode == 'folder':
            if not os.path.exists(input_full_path):
                QMessageBox.warning(
                    None, "Error",
                    f"Input directory '{input_full_path}' does not exist. "
                    "Please select a valid directory."
                )
                self.input_widget.browse_button.setFocus()
                return False
        params['input_path'] = input_path
        params['working_path'] = working_path
        return True


class NoiseDetectionConfigurator(DefaultActionConfigurator):
    METHOD_OPTIONS = ['Norm, LAB', 'Norm, RGB', 'Individual channels, RGB']

    def __init__(self, expert, current_wd):
        super().__init__(expert, current_wd)
        self.method = None
        self.noisy_masked_px = None
        self.channel_thresholds = None

    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.add_field(
            'working_path', FIELD_ABS_PATH, 'Working path', required=True,
            placeholder='inherit from job')
        self.add_field(
            'input_path', FIELD_REL_PATH,
            f'Input path (separate by {constants.PATH_SEPARATOR})',
            required=False, multiple_entries=True,
            placeholder='relative to working path')
        self.add_field(
            'max_frames', FIELD_INT, 'Max. num. of frames (0 = All)',
            required=False,
            default=AppConfig.get('noise_detection_params')['max_frames'], min_val=0, max_val=1000)
        self.method = self.add_field(
            'method', FIELD_COMBO, 'Method', required=False, expert=True,
            options=self.METHOD_OPTIONS, values=constants.VALID_NOISE_METHODS,
            default=dict(zip(constants.VALID_NOISE_METHODS,
                             self.METHOD_OPTIONS))[
                AppConfig.get('noise_detection_params')['method']])
        self.noisy_masked_px = self.add_field(
            'noisy_masked_px', FIELD_INT_TUPLE, 'Noisy pixels to mask',
            required=False, size=3, expert=True,
            default=AppConfig.get('noise_detection_params')['noisy_masked_px'],
            labels=constants.RGB_LABELS, min_val=[0] * 3, max_val=[2000] * 3)
        self.channel_thresholds = self.add_field(
            'channel_thresholds', FIELD_INT_TUPLE, 'Noise threshold',
            required=False, size=3, expert=True,
            default=AppConfig.get('noise_detection_params')['channel_thresholds'],
            labels=constants.RGB_LABELS, min_val=[1] * 3, max_val=[1000] * 3)

        masked_px_spins = self.noisy_masked_px.findChildren(QSpinBox)
        masked_px_labels = self.noisy_masked_px.findChildren(QLabel)
        thresholds_spins = self.channel_thresholds.findChildren(QSpinBox)
        thresholds_labels = self.channel_thresholds.findChildren(QLabel)

        def change_method():
            method = self.method.currentText()
            if method == self.METHOD_OPTIONS[2]:
                for i, (si, li, so, lo) in enumerate(zip(masked_px_spins, masked_px_labels,
                                                         thresholds_spins, thresholds_labels)):
                    si.setEnabled(True)
                    si.show()
                    li.setText(constants.RGB_LABELS[i].upper())
                    li.show()
                    lo.setText(constants.RGB_LABELS[i].upper())
                    lo.show()
                    if si.value() == 0:
                        so.setEnabled(True)
                    so.show()
            else:
                for i, (si, li, so, lo) in enumerate(zip(masked_px_spins, masked_px_labels,
                                                         thresholds_spins, thresholds_labels)):
                    li.setText('')
                    li.hide()
                    lo.setText('')
                    lo.hide()
                    if i == 0:
                        si.setEnabled(True)
                        if si.value() == 0:
                            so.setEnabled(True)
                    else:
                        si.setEnabled(False)
                        si.hide()
                        so.setEnabled(False)
                        so.hide()

        self.method.currentIndexChanged.connect(change_method)
        change_method()

        self.add_field(
            'blur_size', FIELD_INT, 'Blur size (px)', required=False,
            expert=True,
            default=AppConfig.get('noise_detection_params')['blur_size'], min_val=1, max_val=50)
        self.add_field(
            'file_name', FIELD_TEXT, 'File name', required=False,
            default=AppConfig.get('noise_detection_params')['noise_map_filename'],
            placeholder=AppConfig.get('noise_detection_params')['noise_map_filename'])
        self.add_bold_label("Miscellanea:")
        self.add_field(
            'plot_histograms', FIELD_BOOL, 'Plot histograms', required=False,
            default=AppConfig.get('noise_detection_params')['plot_histograms'])
        self.add_field(
            'plot_path', FIELD_REL_PATH, 'Plots path', required=False,
            default=AppConfig.get('image_sequence_manager')['plots_path'],
            placeholder='relative to working path')


class FocusStackBaseConfigurator(DefaultActionConfigurator):
    ENERGY_OPTIONS = ['Tenengrad', 'Variance', 'Laplacian', 'Mod. Laplacian', 'Sobel']
    MAP_TYPE_OPTIONS = ['Average', 'Maximum']
    FLOAT_OPTIONS = ['float 32 bits', 'float 64 bits']
    PY_MODE_OPTIONS = ['Auto', 'All in memory', 'Tiled I/O buffered']
    BLEND_METHODS_OPTIONS = ['Pyramid', 'Bilateral']
    DM_MODE_OPTIONS = ['Auto', 'All in memory', 'I/O buffered']
    NAMING_MODE_OPTIONS = ['Prefix', 'Template']
    NAMING_MODE_VALUES = ['PREFIX', 'TEMPLATE']

    def __init__(self, expert, current_wd):
        super().__init__(expert, current_wd)
        self.tab_widget = None
        self.general_tab_layout = None
        self.algorithm_tab_layout = None
        self.depthmap_energy = None
        self.depthmap_kernel_size = None
        self.depthmap_blur_size = None
        self.depthmap_energy_smooth_size = None
        self.depthmap_energy_sigma_color = None
        self.depthmap_energy_sigma_space = None
        self.depthmap_weights_smooth_size = None
        self.depthmap_weights_sigma_color = None
        self.depthmap_weights_sigma_space = None
        self.depthmap_temperature = None
        self.depthmap_map_type = None
        self.naming_mode_field = None
        self.prefix_field = None
        self.template_field = None

    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.tab_widget = create_tab_widget(layout)
        self.general_tab_layout = add_tab(self.tab_widget, "General Parameters")
        self.create_general_tab(self.general_tab_layout)
        self.algorithm_tab_layout = add_tab(self.tab_widget, "Stacking Algorithm")
        self.create_algorithm_tab(self.algorithm_tab_layout)

    def create_general_tab(self, layout):
        self.add_field_to_layout(
            layout, 'working_path', FIELD_ABS_PATH, 'Working path', required=False,
            expert=True)
        self.add_field_to_layout(
            layout, 'input_path', FIELD_REL_PATH, 'Input path', required=False,
            expert=True, placeholder='relative to working path')
        self.add_field_to_layout(
            layout, 'output_path', FIELD_REL_PATH, 'Output path', required=False,
            expert=True, placeholder='relative to working path')
        self.add_field_to_layout(
            layout, 'scratch_output_dir', FIELD_BOOL, 'Scratch output folder before run',
            required=False, default=True)
        self.add_field_to_layout(
            layout, 'plot_path', FIELD_REL_PATH, 'Plots path', required=False,
            expert=True, default="plots", placeholder='relative to working path')
        self.add_field_to_layout(
            layout, 'denoise_amount', FIELD_FLOAT, 'Denoise, amount', required=False,
            expert=False, default=AppConfig.get('focus_stack_params')['denoise_amount'],
            min_val=0.0, max_val=10.0, step=0.05)
        self.add_field_to_layout(
            layout, 'sharpen_amount_percent', FIELD_FLOAT, 'Sharpen, amount (%)', required=False,
            expert=False, default=AppConfig.get('focus_stack_params')['sharpen_amount_percent'],
            min_val=0.0, max_val=300.0, step=0.5, decimals=1)
        self.add_field_to_layout(
            layout, 'sharpen_radius', FIELD_FLOAT, 'Sharpen, radius (px)', required=False,
            expert=False, default=AppConfig.get('focus_stack_params')['sharpen_radius'],
            min_val=0.0, max_val=4.0, step=0.05)
        self.add_field_to_layout(
            layout, 'sharpen_threshold', FIELD_FLOAT, 'Sharpen, threshold', required=False,
            expert=False, default=AppConfig.get('focus_stack_params')['sharpen_threshold'],
            min_val=0.0, max_val=64.0, step=1)
        self.naming_mode_field = self.add_field_to_layout(
            layout, 'naming_mode', FIELD_COMBO,
            'Filename mode', required=True,
            options=self.NAMING_MODE_OPTIONS,
            values=self.NAMING_MODE_VALUES,
            default='PREFIX')
        self.prefix_field = self.add_field_to_layout(
            layout, 'prefix', FIELD_TEXT,
            'Output filename prefix', required=False,
            expert=True)
        self.template_field = self.add_field_to_layout(
            layout, 'output_file_template', FIELD_TEXT,
            'Output filename template', required=False,
            expert=True)
        self.naming_mode_field.currentIndexChanged.connect(self.change_naming_mode)
        self.change_naming_mode()

    def create_algorithm_tab(self, layout):
        self.add_bold_label_to_layout(layout, "Stacking algorithm:")
        combo = self.add_field_to_layout(
            layout, 'stacker', FIELD_COMBO, 'Stacking algorithm', required=True,
            options=constants.STACK_ALGO_OPTIONS,
            default=AppConfig.get('stacker'))
        q_pyramid, q_depthmap = QWidget(), QWidget()
        for q in [q_pyramid, q_depthmap]:
            q.setLayout(create_tab_layout())
        stacked = QStackedWidget()
        stacked.addWidget(q_pyramid)
        stacked.addWidget(q_depthmap)

        def change():
            text = combo.currentText()
            if text == constants.STACK_ALGO_PYRAMID:
                stacked.setCurrentWidget(q_pyramid)
            elif text == constants.STACK_ALGO_DEPTH_MAP:
                stacked.setCurrentWidget(q_depthmap)

        change()
        self.add_field_to_layout(
            q_pyramid.layout(), 'pyramid_min_size', FIELD_INT, 'Minimum size (px)',
            expert=True,
            required=False, default=AppConfig.get('pyramid_params')['min_size'],
            min_val=2, max_val=256)
        self.add_field_to_layout(
            q_pyramid.layout(), 'pyramid_kernel_size', FIELD_INT, 'Kernel size (px)',
            expert=True,
            required=False, default=AppConfig.get('pyramid_params')['kernel_size'],
            min_val=3, max_val=21)
        self.add_field_to_layout(
            q_pyramid.layout(), 'pyramid_gen_kernel', FIELD_FLOAT, 'Gen. kernel',
            expert=True,
            required=False, default=AppConfig.get('pyramid_params')['gen_kernel'],
            min_val=0.0, max_val=2.0)
        self.add_field_to_layout(
            q_pyramid.layout(), 'pyramid_float_type', FIELD_COMBO, 'Precision', required=False,
            expert=True,
            options=self.FLOAT_OPTIONS, values=constants.VALID_FLOATS,
            default=dict(zip(constants.VALID_FLOATS,
                             self.FLOAT_OPTIONS))[AppConfig.get('pyramid_params')['float_type']])
        py_mode = self.add_field_to_layout(
            q_pyramid.layout(), 'pyramid_mode', FIELD_COMBO, 'Mode',
            expert=True,
            required=False, options=self.PY_MODE_OPTIONS, values=constants.PY_VALID_MODES,
            default=dict(zip(constants.PY_VALID_MODES,
                             self.PY_MODE_OPTIONS))[AppConfig.get('pyramid_params')['mode']])
        py_memory_limit = self.add_field_to_layout(
            q_pyramid.layout(), 'pyramid_memory_limit', FIELD_FLOAT,
            'Memory limit (approx., GBytes)',
            expert=True,
            required=False, default=AppConfig.get('focus_stack_params')['memory_limit'],
            min_val=1.0, max_val=1024.0)
        max_threads = self.add_field_to_layout(
            q_pyramid.layout(), 'pyramid_max_threads', FIELD_INT, 'Max num. of cores',
            expert=True,
            required=False, default=AppConfig.get('focus_stack_params')['max_threads'],
            min_val=1, max_val=256)
        tile_size = self.add_field_to_layout(
            q_pyramid.layout(), 'pyramid_tile_size', FIELD_INT, 'Tile size (px)',
            expert=True,
            required=False, default=AppConfig.get('pyramid_params')['tile_size'],
            min_val=128, max_val=2048)
        n_tiled_layers = self.add_field_to_layout(
            q_pyramid.layout(), 'pyramid_n_tiled_layers', FIELD_INT, 'Num. tiled layers',
            expert=True,
            required=False, default=AppConfig.get('pyramid_params')['n_tiled_layers'],
            min_val=0, max_val=6)

        def change_py_mode():
            text = py_mode.currentText()
            enabled = text == self.PY_MODE_OPTIONS[2]
            tile_size.setEnabled(enabled)
            n_tiled_layers.setEnabled(enabled)
            py_memory_limit.setEnabled(text == self.PY_MODE_OPTIONS[0])
            max_threads.setEnabled(text != self.PY_MODE_OPTIONS[1])

        py_mode.currentIndexChanged.connect(change_py_mode)
        change_py_mode()

        self.depthmap_energy = self.add_field_to_layout(
            q_depthmap.layout(), 'depthmap_energy', FIELD_COMBO, 'Energy', required=False,
            options=self.ENERGY_OPTIONS, values=constants.VALID_DM_ENERGY,
            default=dict(zip(constants.VALID_DM_ENERGY,
                             self.ENERGY_OPTIONS))[AppConfig.get('depth_map_params')['energy']])
        self.depthmap_kernel_size = self.add_field_to_layout(
            q_depthmap.layout(), 'depthmap_kernel_size', FIELD_INT, 'Laplacian kernel size (px)',
            expert=True,
            required=False, default=AppConfig.get('depth_map_params')['kernel_size'],
            min_val=1, max_val=256)
        self.depthmap_blur_size = self.add_field_to_layout(
            q_depthmap.layout(), 'depthmap_blur_size', FIELD_INT, 'Laplacian blur size (px)',
            expert=True,
            required=False, default=AppConfig.get('depth_map_params')['blur_size'],
            min_val=1, max_val=256)

        def change_depthmap_energy():
            enabled = self.depthmap_energy.currentText() == self.ENERGY_OPTIONS[2]
            self.depthmap_kernel_size.setEnabled(enabled)
            self.depthmap_blur_size.setEnabled(enabled)

        self.depthmap_energy.currentIndexChanged.connect(change_depthmap_energy)
        change_depthmap_energy()

        self.depthmap_map_type = self.add_field_to_layout(
            q_depthmap.layout(), 'depthmap_map_type', FIELD_COMBO, 'Map type', required=False,
            options=self.MAP_TYPE_OPTIONS, values=constants.VALID_DM_MAP,
            default=dict(zip(constants.VALID_DM_MAP,
                             self.MAP_TYPE_OPTIONS))[AppConfig.get('depth_map_params')['map_type']])
        self.add_field_to_layout(
            q_depthmap.layout(), 'depthmap_weight_power', FIELD_FLOAT, 'Weight power correction',
            expert=True,
            required=False, default=AppConfig.get('depth_map_params')['weight_power'],
            min_val=0.1, max_val=10, step=0.05)
        self.depthmap_energy_smooth_size = self.add_field_to_layout(
            q_depthmap.layout(), 'depthmap_pyramid_levels', FIELD_INT,
            'Pyramid levels',
            expert=True,
            required=False, default=AppConfig.get('depth_map_params')['pyramid_levels'],
            min_val=1, max_val=10)
        self.depthmap_energy_smooth_size = self.add_field_to_layout(
            q_depthmap.layout(), 'depthmap_energy_smooth_size', FIELD_INT,
            'Energy smooth size (px)',
            expert=True,
            required=False, default=AppConfig.get('depth_map_params')['energy_smooth_size'],
            min_val=0, max_val=256)
        self.depthmap_energy_sigma_color = self.add_field_to_layout(
            q_depthmap.layout(), 'depthmap_energy_sigma_color', FIELD_FLOAT,
            'Energy filter σ, color',
            expert=True,
            required=False, default=AppConfig.get('depth_map_params')['energy_sigma_color'],
            min_val=0, max_val=10, step=0.1)
        self.depthmap_energy_sigma_space = self.add_field_to_layout(
            q_depthmap.layout(), 'depthmap_energy_sigma_space', FIELD_INT,
            'Energy filter σ, space (px)',
            expert=True,
            required=False, default=AppConfig.get('depth_map_params')['energy_sigma_space'],
            min_val=0, max_val=256)

        def change_depthmap_energy_smooth_size():
            enabled = self.depthmap_energy_smooth_size.value() > 0
            self.depthmap_energy_sigma_color.setEnabled(enabled)
            self.depthmap_energy_sigma_space.setEnabled(enabled)

        self.depthmap_energy_smooth_size.valueChanged.connect(
            change_depthmap_energy_smooth_size)
        change_depthmap_energy_smooth_size()

        self.depthmap_weights_smooth_size = self.add_field_to_layout(
            q_depthmap.layout(), 'depthmap_pyramid_smooth_size', FIELD_INT,
            'Pyramid smooth size (px)',
            expert=True,
            required=False, default=AppConfig.get('depth_map_params')['pyramid_smooth_size'],
            min_val=0, max_val=256)
        self.depthmap_temperature = self.add_field_to_layout(
            q_depthmap.layout(), 'depthmap_temperature', FIELD_FLOAT, 'Temperature',
            expert=True,
            required=False, default=AppConfig.get('depth_map_params')['temperature'],
            min_val=0, max_val=1000, decimals=1, step=0.1)

        def change_depthmap_map_type():
            enabled = self.depthmap_map_type.currentText() == self.MAP_TYPE_OPTIONS[1]
            self.depthmap_temperature.setEnabled(enabled)

        self.depthmap_map_type.currentIndexChanged.connect(
            change_depthmap_map_type)
        change_depthmap_map_type()

        self.add_field_to_layout(
            q_depthmap.layout(), 'depthmap_float_type', FIELD_COMBO,
            'Precision', required=False,
            expert=True,
            options=self.FLOAT_OPTIONS, values=constants.VALID_FLOATS,
            default=dict(zip(constants.VALID_FLOATS,
                             self.FLOAT_OPTIONS))[AppConfig.get('depth_map_params')['float_type']])
        dm_mode = self.add_field_to_layout(
            q_depthmap.layout(), 'depthmap_mode', FIELD_COMBO, 'Mode',
            expert=True,
            required=False, options=self.DM_MODE_OPTIONS, values=constants.DM_VALID_MODES,
            default=dict(zip(constants.DM_VALID_MODES,
                             self.DM_MODE_OPTIONS))[AppConfig.get('depth_map_params')['mode']])
        dm_memory_limit = self.add_field_to_layout(
            q_depthmap.layout(), 'depthmap_memory_limit', FIELD_FLOAT,
            'Memory limit (approx., GBytes)',
            expert=True,
            required=False, default=AppConfig.get('focus_stack_params')['memory_limit'],
            min_val=1.0, max_val=1024.0)

        def change_dm_mode():
            text = dm_mode.currentText()
            dm_memory_limit.setEnabled(text == self.PY_MODE_OPTIONS[0])

        dm_mode.currentIndexChanged.connect(change_dm_mode)
        change_dm_mode()

        layout.addRow(stacked)
        combo.currentIndexChanged.connect(change)
        self.add_field_to_layout(
            q_depthmap.layout(), 'depthmap_plot_depth_map', FIELD_BOOL, 'Plot depth map',
            required=False, default=AppConfig.get('depth_map_params')['plot_depth_map'])

    def change_naming_mode(self):
        current_text = self.naming_mode_field.currentText()
        if current_text == self.NAMING_MODE_OPTIONS[0]:  # 'Prefix'
            self.prefix_field.setEnabled(True)
            self.template_field.setEnabled(False)
        else:  # 'Template'
            self.prefix_field.setEnabled(False)
            self.template_field.setEnabled(True)

    def set_naming_defaults(self, naming_mode, prefix, output_file_template):
        display_text = dict(zip(self.NAMING_MODE_VALUES, self.NAMING_MODE_OPTIONS))[naming_mode]
        self.naming_mode_field.setCurrentText(display_text)
        self.prefix_field.setText(prefix)
        self.prefix_field.setPlaceholderText(prefix)
        if naming_mode == 'TEMPLATE':
            self.template_field.setText(output_file_template)
        else:
            self.template_field.setText("")
        self.template_field.setPlaceholderText(output_file_template)
        self.change_naming_mode()

    def clear_inactive_param(self, params):
        current_text = self.naming_mode_field.currentText()
        if current_text == self.NAMING_MODE_OPTIONS[0]:  # 'Prefix'
            self.template_field.setText("")
            params.pop('output_file_template', None)
        else:  # 'Template'
            self.prefix_field.setText("")
            params.pop('prefix', None)
        return params

    def update_params(self, params):
        result = super().update_params(params)
        current_text = self.naming_mode_field.currentText()
        if current_text == self.NAMING_MODE_OPTIONS[0]:  # 'Prefix'
            params.pop('output_file_template', None)
        else:  # 'Template'
            params.pop('prefix', None)
        return result


class FocusStackConfigurator(FocusStackBaseConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        focus_defaults = AppConfig.get('focus_stack_params')
        naming_mode = action.params.get('naming_mode', focus_defaults.get('naming_mode', 'PREFIX'))
        self.set_naming_defaults(
            naming_mode,
            action.params.get('prefix', focus_defaults['prefix']),
            action.params.get('output_file_template', focus_defaults['output_file_template'])
        )
        self.add_field_to_layout(
            self.general_tab_layout, 'exif_path', FIELD_REL_PATH,
            'Exif data path', required=False,
            expert=True,
            placeholder='relative to working path')

        self.add_field_to_layout(
            self.general_tab_layout, 'plot_stack', FIELD_BOOL, 'Plot stack', required=False,
            default=focus_defaults['plot_stack'])


class FocusStackBunchConfigurator(FocusStackBaseConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        bunch_defaults = AppConfig.get('focus_stack_bunch_params')
        naming_mode = action.params.get('naming_mode', bunch_defaults.get('naming_mode', 'PREFIX'))
        self.set_naming_defaults(
            naming_mode,
            action.params.get('prefix', bunch_defaults['prefix']),
            action.params.get('output_file_template', bunch_defaults['output_file_template'])
        )
        self.add_field_to_layout(
            self.general_tab_layout, 'frames', FIELD_INT, 'Frames', required=False,
            default=bunch_defaults['frames'],
            min_val=1, max_val=100)
        self.add_field_to_layout(
            self.general_tab_layout, 'overlap', FIELD_INT, 'Overlapping frames', required=False,
            default=bunch_defaults['overlap'], min_val=0, max_val=100)
        self.add_field_to_layout(
            self.general_tab_layout, 'delete_output_at_end', FIELD_BOOL,
            'Delete output at end of job',
            required=False, default=False)
        self.add_field_to_layout(
            self.general_tab_layout, 'plot_stack', FIELD_BOOL, 'Plot stack', required=False,
            default=bunch_defaults['plot_stack'])


class MultiLayerConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.add_field(
            'working_path', FIELD_ABS_PATH, 'Working path', required=False,
            expert=True)
        self.add_field(
            'input_path', FIELD_REL_PATH,
            f'Input path (separate by {constants.PATH_SEPARATOR})',
            required=False, multiple_entries=True,
            placeholder='relative to working path')
        self.add_field(
            'output_path', FIELD_REL_PATH, 'Output path', required=False,
            expert=True,
            placeholder='relative to working path')
        self.add_field(
            'exif_path', FIELD_REL_PATH, 'Exif data path', required=False,
            expert=True,
            placeholder='relative to working path')
        self.add_field(
            'scratch_output_dir', FIELD_BOOL, 'Scratch output folder before run',
            required=False, default=True)
        self.add_field(
            'reverse_order', FIELD_BOOL, 'Reverse file order', required=False,
            default=AppConfig.get('multilayer_params')['file_reverse_order'])


class CombinedActionsConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.add_field(
            'working_path', FIELD_ABS_PATH, 'Working path', required=False,
            expert=True)
        self.add_field(
            'input_path', FIELD_REL_PATH, 'Input path', required=False,
            expert=True,
            must_exist=True, placeholder='relative to working path')
        self.add_field(
            'output_path', FIELD_REL_PATH, 'Output path', required=False,
            expert=True,
            placeholder='relative to working path')
        self.add_field(
            'scratch_output_dir', FIELD_BOOL, 'Scratch output folder before run',
            required=False, default=True)
        self.add_field(
            'delete_output_at_end', FIELD_BOOL, 'Delete output at end of job',
            required=False, default=False)
        self.add_field(
            'plot_path', FIELD_REL_PATH, 'Plots path', required=False,
            expert=True,
            default="plots", placeholder='relative to working path')
        self.add_field(
            'resample', FIELD_INT, 'Resample frame stack', required=False,
            expert=True,
            default=1, min_val=1, max_val=100)
        self.add_field(
            'reference_index', FIELD_REF_IDX, 'Reference frame', required=False,
            expert=True,
            default=0)
        self.add_field(
            'step_process', FIELD_BOOL, 'Step process', required=False,
            expert=True, default=AppConfig.get('reference_frame_task')['step_process'])
        self.add_field(
            'max_threads', FIELD_INT, 'Max num. of cores',
            required=False, default=AppConfig.get('combined_actions_params')['max_threads'],
            expert=True,
            min_val=1, max_val=256)
        self.add_field(
            'chunk_submit', FIELD_BOOL, 'Submit in chunks',
            expert=True,
            required=False, default=AppConfig.get('sequential_task')['chunk_submit'])


class MaskNoiseConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.add_field(
            'noise_mask', FIELD_REL_PATH, 'Noise mask file', required=False,
            path_type='file', must_exist=True, skip_working_path_check=True,
            default=AppConfig.get('noise_detection_params')['noise_map_filename'],
            placeholder=AppConfig.get('noise_detection_params')['noise_map_filename'])
        self.add_field(
            'kernel_size', FIELD_INT, 'Kernel size', required=False,
            expert=True,
            default=AppConfig.get('mask_noise_params')['kernel_size'], min_val=1, max_val=10)
        self.add_field(
            'method', FIELD_COMBO, 'Interpolation method', required=False,
            expert=True,
            options=['Mean', 'Median'],
            default=AppConfig.get('mask_noise_params')['method'])
        self.add_field(
            'max_noisy_pxls', FIELD_INT, 'Max. n. of noisy pixels', required=False,
            expert=True,
            default=AppConfig.get('mask_noise_params')['max_noisy_pxls'],
            min_val=1, max_val=10000)


class SubsampleActionConfigurator(DefaultActionConfigurator):
    def __init__(self, expert, current_wd):
        super().__init__(expert, current_wd)
        self.subsample_field = None
        self.fast_subsampling_field = None

    def add_subsample_fields(
            self, default_subsample, default_fast_subsampling, add_to_layout=None):
        if add_to_layout is None:
            add_to_layout = self.builder.main_layout
        self.subsample_field = self.add_field(
            'subsample', FIELD_COMBO, 'Subsample', required=False,
            expert=True,
            options=constants.FIELD_SUBSAMPLE_OPTIONS,
            values=constants.FIELD_SUBSAMPLE_VALUES,
            default=default_subsample,
            add_to_layout=add_to_layout)
        self.fast_subsampling_field = self.add_field(
            'fast_subsampling', FIELD_BOOL, 'Fast subsampling', required=False,
            expert=True,
            default=default_fast_subsampling,
            add_to_layout=add_to_layout)

        self.subsample_field.currentTextChanged.connect(self.change_subsample)
        self.change_subsample()

    def change_subsample(self):
        self.fast_subsampling_field.setEnabled(
            self.subsample_field.currentText() not in constants.FIELD_SUBSAMPLE_OPTIONS[:2])


class AlignFramesConfigBase:
    TRANSFORM_OPTIONS = ['Rigid', 'Homography']
    MATCHING_METHOD_OPTIONS = ['K-nearest neighbors', 'Hamming distance']
    DETECTOR_DESCRIPTOR_TOOLTIPS = {
        'detector':
            "SIFT: Requires SIFT descriptor and K-NN matching\n"
            "ORB/AKAZE: Work best with Hamming distance",
        'descriptor':
            "SIFT: Requires K-NN matching\n"
            "ORB/AKAZE: Require Hamming distance with ORB/AKAZE detectors",
        'match_method':
            "Automatically selected based on detector/descriptor combination"
    }

    def __init__(self):
        self.info_label = None

    def show_info(self, message, timeout=3000):
        self.info_label.setText(message)
        timer = QTimer(self.info_label)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self.info_label.setText(''))
        timer.start(timeout)

    def change_match_config(
            self, detector_field, descriptor_field, matching_method_field, show_info):
        detector = detector_field.currentText()
        descriptor = descriptor_field.currentText()
        match_method = dict(
            zip(self.MATCHING_METHOD_OPTIONS,
                constants.VALID_MATCHING_METHODS))[matching_method_field.currentText()]
        try:
            validate_align_config(detector, descriptor, match_method)
        except Exception as e:
            show_info(str(e))
            if descriptor == constants.DETECTOR_SIFT and \
               match_method == constants.MATCHING_NORM_HAMMING:
                matching_method_field.setCurrentText(self.MATCHING_METHOD_OPTIONS[0])
            if detector == constants.DETECTOR_ORB and descriptor == constants.DESCRIPTOR_AKAZE and \
                    match_method == constants.MATCHING_NORM_HAMMING:
                matching_method_field.setCurrentText(constants.MATCHING_NORM_HAMMING)
            if detector == constants.DETECTOR_BRISK and descriptor == constants.DESCRIPTOR_AKAZE:
                descriptor_field.setCurrentText('BRISK')
            if detector == constants.DETECTOR_SURF and descriptor == constants.DESCRIPTOR_AKAZE:
                descriptor_field.setCurrentText('SIFT')
            if detector == constants.DETECTOR_SIFT and descriptor != constants.DESCRIPTOR_SIFT:
                descriptor_field.setCurrentText('SIFT')
            if detector in constants.NOKNN_METHODS['detectors'] and \
               descriptor in constants.NOKNN_METHODS['descriptors']:
                if match_method == constants.MATCHING_KNN:
                    matching_method_field.setCurrentText(self.MATCHING_METHOD_OPTIONS[1])


class AlignFramesConfigurator(SubsampleActionConfigurator, AlignFramesConfigBase):
    BORDER_MODE_OPTIONS = ['Constant', 'Replicate', 'Replicate and blur']
    METHOD_OPTIONS = ['Random Sample Consensus (RANSAC)', 'Least Median (LMEDS)']
    MODE_OPTIONS = ['Auto', 'Sequential', 'Parallel']

    def __init__(self, expert, current_wd):
        SubsampleActionConfigurator.__init__(self, expert, current_wd)
        AlignFramesConfigBase.__init__(self)
        self.matching_method_field = None
        self.detector_field = None
        self.descriptor_field = None
        self.matching_method_field = None
        self.tab_widget = None
        self.current_tab_layout = None

    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.detector_field = None
        self.descriptor_field = None
        self.matching_method_field = None
        self.tab_widget = create_tab_widget(layout)
        feature_layout = add_tab(self.tab_widget, "Feature extraction")
        self.create_feature_tab(feature_layout)
        transform_layout = add_tab(self.tab_widget, "Transform")
        self.create_transform_tab(transform_layout)
        border_layout = add_tab(self.tab_widget, "Border")
        self.create_border_tab(border_layout)
        misc_layout = add_tab(self.tab_widget, "Miscellanea")
        self.create_miscellanea_tab(misc_layout)

    def create_feature_tab(self, layout):

        def change_match_config():
            self.change_match_config(
                self.detector_field, self.descriptor_field,
                self. matching_method_field, self.show_info)
        self.add_bold_label_to_layout(layout, "Feature identification:")
        self.detector_field = self.add_field_to_layout(
            layout, 'detector', FIELD_COMBO, 'Detector', required=False,
            options=constants.VALID_DETECTORS, default=AppConfig.get('detector'))
        self.descriptor_field = self.add_field_to_layout(
            layout, 'descriptor', FIELD_COMBO, 'Descriptor', required=False,
            options=constants.VALID_DESCRIPTORS, default=AppConfig.get('descriptor'))
        self.detector_field.setToolTip(self.DETECTOR_DESCRIPTOR_TOOLTIPS['detector'])
        self.descriptor_field.setToolTip(self.DETECTOR_DESCRIPTOR_TOOLTIPS['descriptor'])
        self.detector_field.currentIndexChanged.connect(change_match_config)
        self.descriptor_field.currentIndexChanged.connect(change_match_config)
        self.info_label = QLabel()
        self.info_label.setStyleSheet("color: orange; font-style: italic;")
        layout.addRow(self.info_label)
        self.add_bold_label_to_layout(layout, "Feature matching:")
        self.matching_method_field = self.add_field_to_layout(
            layout, 'match_method', FIELD_COMBO, 'Match method', required=False,
            options=self.MATCHING_METHOD_OPTIONS, values=constants.VALID_MATCHING_METHODS,
            default=AppConfig.get('match_method'))
        self.matching_method_field.setToolTip(self.DETECTOR_DESCRIPTOR_TOOLTIPS['match_method'])
        self.matching_method_field.currentIndexChanged.connect(change_match_config)
        self.add_field_to_layout(
            layout, 'flann_idx_kdtree', FIELD_INT, 'Flann idx kdtree', required=False,
            expert=True,
            default=AppConfig.get('align_frames_params')['flann_idx_kdtree'],
            min_val=0, max_val=10)
        self.add_field_to_layout(
            layout, 'flann_trees', FIELD_INT, 'Flann trees', required=False,
            expert=True,
            default=AppConfig.get('align_frames_params')['flann_trees'],
            min_val=0, max_val=10)
        self.add_field_to_layout(
            layout, 'flann_checks', FIELD_INT, 'Flann checks', required=False,
            expert=True,
            default=AppConfig.get('align_frames_params')['flann_checks'],
            min_val=0, max_val=1000)
        self.add_field_to_layout(
            layout, 'threshold', FIELD_FLOAT, 'Threshold', required=False,
            expert=True,
            default=AppConfig.get('align_frames_params')['threshold'],
            min_val=0, max_val=1, step=0.05)
        self.add_subsample_fields(
            default_subsample=AppConfig.get('align_frames_params')['subsample'],
            default_fast_subsampling=AppConfig.get('align_frames_params')['fast_subsampling'],
            add_to_layout=layout)

    def create_transform_tab(self, layout):
        self.add_bold_label_to_layout(layout, "Transform:")
        transform = self.add_field_to_layout(
            layout, 'transform', FIELD_COMBO, 'Transform', required=False,
            options=self.TRANSFORM_OPTIONS, values=constants.VALID_TRANSFORMS,
            default=AppConfig.get('align_frames_params')['transform'])
        method = self.add_field_to_layout(
            layout, 'align_method', FIELD_COMBO, 'Estimation method', required=False,
            options=self.METHOD_OPTIONS, values=constants.VALID_ESTIMATION_METHODS,
            default=AppConfig.get('align_frames_params')['align_method'])
        rans_threshold = self.add_field_to_layout(
            layout, 'rans_threshold', FIELD_FLOAT, 'RANSAC threshold (px)', required=False,
            expert=True,
            default=AppConfig.get('align_frames_params')['rans_threshold'],
            min_val=0, max_val=20, step=0.1)
        self.add_field_to_layout(
            layout, 'min_good_matches', FIELD_INT, "Min. good matches", required=False,
            expert=True,
            default=AppConfig.get('align_frames_params')['min_good_matches'],
            min_val=0, max_val=500)

        def change_method():
            text = method.currentText()
            if text == self.METHOD_OPTIONS[0]:
                rans_threshold.setEnabled(True)
            elif text == self.METHOD_OPTIONS[1]:
                rans_threshold.setEnabled(False)

        method.currentIndexChanged.connect(change_method)
        change_method()
        self.add_field_to_layout(
            layout, 'align_confidence', FIELD_FLOAT, 'Confidence (%)',
            required=False, decimals=1,
            expert=True,
            default=AppConfig.get('align_frames_params')['align_confidence'],
            min_val=70.0, max_val=100.0, step=0.1)
        refine_iters = self.add_field_to_layout(
            layout, 'refine_iters', FIELD_INT, 'Refinement iterations (Rigid)', required=False,
            expert=True,
            default=AppConfig.get('align_frames_params')['refine_iters'], min_val=0, max_val=1000)
        max_iters = self.add_field_to_layout(
            layout, 'max_iters', FIELD_INT, 'Max. iterations (Homography)', required=False,
            expert=True,
            default=AppConfig.get('align_frames_params')['max_iters'], min_val=0, max_val=5000)

        def change_transform():
            text = transform.currentText()
            if text == self.TRANSFORM_OPTIONS[0]:
                refine_iters.setEnabled(True)
                max_iters.setEnabled(False)
            elif text == self.TRANSFORM_OPTIONS[1]:
                refine_iters.setEnabled(False)
                max_iters.setEnabled(True)

        transform.currentIndexChanged.connect(change_transform)
        change_transform()
        phase_corr_fallback = self.add_field_to_layout(
            layout, 'phase_corr_fallback', FIELD_BOOL, "Phase correlation as fallback",
            required=False, expert=True,
            default=AppConfig.get('align_frames_params')['phase_corr_fallback'])
        phase_corr_fallback.setToolTip(
            "Align using phase correlation algorithm if the number of matches\n"
            "is too low to determine the transformation.\n"
            "This algorithm is not very precise,\n"
            "and may help only in case of blurred images.")
        self.add_field_to_layout(
            layout, 'abort_abnormal', FIELD_BOOL, 'Abort on abnormal transf.',
            expert=True,
            required=False, default=AppConfig.get('align_frames_params')['abort_abnormal'])

    def create_border_tab(self, layout):
        self.add_bold_label_to_layout(layout, "Border:")
        self.add_field_to_layout(
            layout, 'border_mode', FIELD_COMBO, 'Border mode', required=False,
            options=self.BORDER_MODE_OPTIONS,
            values=constants.VALID_BORDER_MODES,
            default=AppConfig.get('align_frames_params')['border_mode'])
        self.add_field_to_layout(
            layout, 'border_value', FIELD_INT_TUPLE,
            'Border value (if constant)', required=False, size=4,
            expert=True,
            default=AppConfig.get('align_frames_params')['border_mode'],
            labels=constants.RGBA_LABELS,
            min_val=[0] * 4, max_val=[255] * 4)
        self.add_field_to_layout(
            layout, 'border_blur', FIELD_FLOAT, 'Border blur', required=False,
            expert=True,
            default=AppConfig.get('align_frames_params')['border_blur'],
            min_val=0, max_val=1000, step=1)

    def create_miscellanea_tab(self, layout):
        self.add_bold_label_to_layout(layout, "Miscellanea:")
        mode = self.add_field_to_layout(
            layout, 'mode', FIELD_COMBO, 'Mode',
            required=False, options=self.MODE_OPTIONS, values=constants.ALIGN_VALID_MODES,
            default=dict(zip(constants.ALIGN_VALID_MODES,
                             self.MODE_OPTIONS))[AppConfig.get(
                                                 'align_frames_params')['align_mode']])
        memory_limit = self.add_field_to_layout(
            layout, 'memory_limit', FIELD_FLOAT, 'Memory limit (approx., GBytes)',
            required=False, default=AppConfig.get('align_frames_params')['memory_limit'],
            min_val=1.0, max_val=1024.0)
        max_threads = self.add_field_to_layout(
            layout, 'max_threads', FIELD_INT, 'Max num. of cores',
            required=False, default=AppConfig.get('align_frames_params')['max_threads'],
            min_val=1, max_val=256)
        chunk_submit = self.add_field_to_layout(
            layout, 'chunk_submit', FIELD_BOOL, 'Submit in chunks',
            expert=True,
            required=False, default=AppConfig.get('align_frames_params')['chunk_submit'])
        bw_matching = self.add_field_to_layout(
            layout, 'bw_matching', FIELD_BOOL, 'Match using black & white',
            expert=True,
            required=False, default=AppConfig.get('align_frames_params')['bw_matching'])
        delta_max = self.add_field_to_layout(
            layout, 'delta_max', FIELD_INT, 'Max frames skip',
            required=False, default=AppConfig.get('align_frames_params')['delta_max'],
            min_val=1, max_val=128)

        def change_mode():
            text = mode.currentText()
            enabled = text != self.MODE_OPTIONS[1]
            memory_limit.setEnabled(enabled)
            max_threads.setEnabled(enabled)
            chunk_submit.setEnabled(enabled)
            bw_matching.setEnabled(enabled)
            delta_max.setEnabled(enabled)

        mode.currentIndexChanged.connect(change_mode)

        self.add_field_to_layout(
            layout, 'plot_summary', FIELD_BOOL, 'Plot summary',
            required=False, default=False)

        self.add_field_to_layout(
            layout, 'plot_matches', FIELD_BOOL, 'Plot matches',
            required=False, default=False)

    def update_params(self, params):
        if self.detector_field and self.descriptor_field and self.matching_method_field:
            try:
                detector = self.detector_field.currentText()
                descriptor = self.descriptor_field.currentText()
                match_method = dict(
                    zip(self.MATCHING_METHOD_OPTIONS,
                        constants.VALID_MATCHING_METHODS))[
                            self.matching_method_field.currentText()]
                validate_align_config(detector, descriptor, match_method)
                return super().update_params(params)
            except Exception as e:
                traceback.print_exc()
                QMessageBox.warning(None, "Error", f"{str(e)}")
                return False
        return super().update_params(params)


class BalanceFramesConfigurator(SubsampleActionConfigurator):
    CORRECTION_MAP_OPTIONS = ['Linear', 'Gamma', 'Match histograms']
    CHANNEL_OPTIONS = ['Luminosity', 'RGB', 'HSV', 'HLS', 'LAB']

    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.add_field(
            'mask_size', FIELD_FLOAT, 'Mask size', required=False,
            expert=True,
            default=AppConfig.get('balance_frames_params')['mask_size'],
            min_val=0, max_val=5, step=0.1)
        self.add_field(
            'intensity_interval', FIELD_INT_TUPLE, 'Intensity range',
            required=False, size=2,
            expert=True,
            default=[v for k, v in
                     AppConfig.get('balance_frames_params')['intensity_interval'].items()],
            labels=['min', 'max'], min_val=[-1] * 2, max_val=[65536] * 2)
        self.add_subsample_fields(
            default_subsample=AppConfig.get('balance_frames_params')['subsample'],
            default_fast_subsampling=AppConfig.get('balance_frames_params')['fast_subsampling'])
        self.add_field(
            'corr_map', FIELD_COMBO, 'Correction map', required=False,
            options=self.CORRECTION_MAP_OPTIONS, values=constants.VALID_BALANCE,
            default=dict(zip(constants.VALID_BALANCE,
                         self.CORRECTION_MAP_OPTIONS))[
                AppConfig.get('balance_frames_params')['corr_map']])
        self.add_field(
            'channel', FIELD_COMBO, 'Channel', required=False,
            options=self.CHANNEL_OPTIONS, values=constants.VALID_BALANCE_CHANNELS,
            default=dict(zip(constants.VALID_BALANCE_CHANNELS,
                         self.CHANNEL_OPTIONS))[
                AppConfig.get('balance_frames_params')['channel']])
        self.add_bold_label("Miscellanea:")
        self.add_field(
            'plot_summary', FIELD_BOOL, 'Plot summary',
            required=False, default=False)
        self.add_field(
            'plot_histograms', FIELD_BOOL, 'Plot histograms',
            required=False, default=False)


class VignettingConfigurator(SubsampleActionConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.add_field(
            'r_steps', FIELD_INT, 'Radial steps', required=False,
            expert=True,
            default=AppConfig.get('vignetting_params')['r_steps'], min_val=1, max_val=1000)
        self.add_field(
            'black_threshold', FIELD_INT, 'Black intensity threshold',
            expert=True,
            required=False, default=AppConfig.get('vignetting_params')['black_threshold'],
            min_val=0, max_val=1000)
        self.add_subsample_fields(
            default_subsample=AppConfig.get('vignetting_params')['subsample'],
            default_fast_subsampling=AppConfig.get('vignetting_params')['fast_subsampling'])
        self.add_field(
            'max_correction', FIELD_FLOAT, 'Max. correction', required=False,
            default=AppConfig.get('vignetting_params')['max_correction'],
            min_val=0, max_val=1, step=0.05)
        self.add_bold_label("Miscellanea:")
        self.add_field(
            'plot_correction', FIELD_BOOL, 'Plot correction', required=False,
            default=False)
        self.add_field(
            'plot_summary', FIELD_BOOL, 'Plot summary', required=False,
            default=False)
