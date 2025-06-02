from PySide6.QtWidgets import (
    QMainWindow, QWidget, QPushButton, QVBoxLayout, QListWidget, QHBoxLayout,
    QFileDialog, QLabel, QComboBox, QMessageBox, QInputDialog,
    QDialog, QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox)
from gui.project_model import Project, Job, ActionConfig
from abc import ABC, abstractmethod
from typing import Dict, Any

COMBO_ACTIONS = "Combined Actions"
ACTION_TYPES = [COMBO_ACTIONS, "FocusStackBunch", "FocusStack", "MultiLayer", "NoiseDetection"]
SUB_ACTION_TYPES = ["MaskNoise", "Vignetting", "AlignFrames", "BalanceFrames"]


class ActionConfigurator(ABC):
    @abstractmethod
    def create_form(self, layout: QFormLayout, params: Dict[str, Any]):
        pass

    @abstractmethod
    def update_params(self, params: Dict[str, Any]):
        pass


class ActionConfigDialog(QDialog):
    def __init__(self, action: ActionConfig, parent=None):
        super().__init__(parent)
        self.action = action
        self.setWindowTitle(f"Configure {action.type_name}")
        self.configurator = self._get_configurator(action.type_name)
        self.layout = QFormLayout(self)
        self.configurator.create_form(self.layout, action.params)
        button_box = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        button_box.addWidget(ok_button)
        button_box.addWidget(cancel_button)
        self.layout.addRow(button_box)
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

    def _get_configurator(self, action_type: str) -> ActionConfigurator:
        configurators = {
            "Job": JobConfigurator(),
            COMBO_ACTIONS: CombinedActionsConfigurator(),
            "NoiseDetection": NoiseDetectionConfigurator(),
            "FocusStack": FocusStackConfigurator(),
            "MultiLayer": MultiLayerConfigurator(),
            # add more configurators here
        }
        return configurators.get(action_type, DefaultActionConfigurator())

    def accept(self):
        self.configurator.update_params(self.action.params)
        super().accept()


class PathConfiguratorMixin:
    def add_path_selection(self, layout, params):
        working_path = params.get('working_path', '')
        self.working_path_edit = QLineEdit(working_path)
        working_path_button = QPushButton("Browse...")

        input_path = params.get('input_path', '')
        self.input_path_edit = QLineEdit(input_path)
        input_path_button = QPushButton("Browse...")

        working_path_button.clicked.connect(self._browse_working_path)
        input_path_button.clicked.connect(self._browse_input_path)

        working_path_layout = QHBoxLayout()
        working_path_layout.addWidget(self.working_path_edit)
        working_path_layout.addWidget(working_path_button)
        layout.addRow("Working Path:", working_path_layout)

        input_path_layout = QHBoxLayout()
        input_path_layout.addWidget(self.input_path_edit)
        input_path_layout.addWidget(input_path_button)
        layout.addRow("Input Path:", input_path_layout)

    def _browse_working_path(self):
        path = QFileDialog.getExistingDirectory(None, "Select Working Directory")
        if path:
            self.working_path_edit.setText(path)

    def _browse_input_path(self):
        path = QFileDialog.getExistingDirectory(None, "Select Input Directory")
        if path:
            self.input_path_edit.setText(path)

    def update_path_params(self, params):
        """Aggiorna i parametri con i percorsi selezionati"""
        params['working_path'] = self.working_path_edit.text()
        params['input_path'] = self.input_path_edit.text()


class DefaultActionConfigurator(ActionConfigurator):
    def create_form(self, layout, params):
        if 'name' not in params:
            params['name'] = ''
        name_edit = QLineEdit(params['name'])
        layout.addRow("Action name:", name_edit)
        self.name_edit = name_edit

    def update_params(self, params):
        params['name'] = self.name_edit.text()


class JobConfigurator(ActionConfigurator, PathConfiguratorMixin):
    def create_form(self, layout, params):
        if 'name' not in params:
            params['name'] = ''
        name_edit = QLineEdit(params['name'])
        layout.addRow("Job name:", name_edit)
        self.name_edit = name_edit
        self.add_path_selection(layout, params)

    def update_params(self, params):
        params['name'] = self.name_edit.text()
        self.update_path_params(params)


class NoiseDetectionConfigurator(ActionConfigurator, PathConfiguratorMixin):
    def create_form(self, layout, params):
        DefaultActionConfigurator().create_form(layout, params)
        self.add_path_selection(layout, params)
        threshold = params.get('threshold', 0.5)
        threshold_spin = QDoubleSpinBox()
        threshold_spin.setValue(threshold)
        threshold_spin.setRange(0, 1)
        threshold_spin.setSingleStep(0.1)
        layout.addRow("Noise threshold:", threshold_spin)
        self.threshold_spin = threshold_spin

    def update_params(self, params):
        params['threshold'] = self.threshold_spin.value()


class FocusStackConfigurator(ActionConfigurator):
    def create_form(self, layout, params):
        DefaultActionConfigurator().create_form(layout, params)
        method = params.get('method', 'pyramids')
        method_combo = QComboBox()
        method_combo.addItems(['pyramids', 'depth map'])
        method_combo.setCurrentText(method)
        layout.addRow("Stacking method:", method_combo)
        self.method_combo = method_combo

    def update_params(self, params):
        params['method'] = self.method_combo.currentText()


class MultiLayerConfigurator(ActionConfigurator):
    def create_form(self, layout, params):
        DefaultActionConfigurator().create_form(layout, params)

        layers = params.get('layers', 3)
        layers_spin = QSpinBox()
        layers_spin.setValue(layers)
        layers_spin.setRange(1, 10)
        layout.addRow("Number of layers:", layers_spin)
        self.layers_spin = layers_spin

        blend_mode = params.get('blend_mode', 'normal')
        blend_combo = QComboBox()
        blend_combo.addItems(['normal', 'multiply', 'screen'])
        blend_combo.setCurrentText(blend_mode)
        layout.addRow("Blend mode:", blend_combo)
        self.blend_combo = blend_combo

    def update_params(self, params):
        params['layers'] = self.layers_spin.value()
        params['blend_mode'] = self.blend_combo.currentText()


class CombinedActionsConfigurator(ActionConfigurator):
    def create_form(self, layout, params):
        DefaultActionConfigurator().create_form(layout, params)

    def update_params(self, params):
        pass


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Focus Stacking GUI")
        self.resize(800, 600)

        self.project = Project()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.job_list = QListWidget()
        self.job_list.currentRowChanged.connect(self.on_job_selected)
        self.job_list.itemDoubleClicked.connect(self.on_job_double_clicked)

        self.action_list = QListWidget()
        self.action_list.itemDoubleClicked.connect(self.on_action_double_clicked)

        self.add_job_button = QPushButton("Add Job")
        self.add_job_button.clicked.connect(self.add_job)

        self.run_job_button = QPushButton("Run Job")
        self.run_job_button.clicked.connect(self.run_job)

        self.run_all_jobs_button = QPushButton("Run All Jobs")
        self.run_all_jobs_button.clicked.connect(self.run_all_jobs)

        self.add_action_button = QPushButton("Add Action")
        self.add_action_button.clicked.connect(self.add_action)

        self.action_selector = QComboBox()
        self.action_selector.addItems(ACTION_TYPES)

        layout = QVBoxLayout()
        hlayout = QHBoxLayout()

        vbox_left = QVBoxLayout()
        vbox_left.addWidget(QLabel("Jobs"))
        vbox_left.addWidget(self.job_list)
        vbox_left.addWidget(self.add_job_button)
        hbox_run = QHBoxLayout()
        hbox_run.addWidget(self.run_job_button)
        hbox_run.addWidget(self.run_all_jobs_button)
        vbox_left.addLayout(hbox_run)

        vbox_right = QVBoxLayout()
        vbox_right.addWidget(QLabel("Actions"))
        vbox_right.addWidget(self.action_list)
        vbox_right.addWidget(QLabel("Select Action Type"))
        vbox_right.addWidget(self.action_selector)
        vbox_right.addWidget(self.add_action_button)

        self.delete_job_button = QPushButton("Delete Job")
        self.delete_job_button.setEnabled(False)
        self.delete_job_button.clicked.connect(self.delete_job)
        vbox_left.addWidget(self.delete_job_button)

        self.job_list.itemSelectionChanged.connect(self.update_delete_buttons_state)
        self.action_list.itemSelectionChanged.connect(self.update_delete_buttons_state)

        self.sub_action_selector = QComboBox()
        self.sub_action_selector.addItems(SUB_ACTION_TYPES)
        self.sub_action_selector.setEnabled(False)

        self.add_sub_action_button = QPushButton("Add Sub-Action")
        self.add_sub_action_button.clicked.connect(self.add_sub_action)
        self.add_sub_action_button.setEnabled(False)

        vbox_right.addWidget(QLabel("Select Sub-Action Type"))
        vbox_right.addWidget(self.sub_action_selector)
        vbox_right.addWidget(self.add_sub_action_button)

        self.delete_action_button = QPushButton("Delete Action")
        self.delete_action_button.setEnabled(False)
        self.delete_action_button.clicked.connect(self.delete_action)
        vbox_right.addWidget(self.delete_action_button)

        hlayout.addLayout(vbox_left)
        hlayout.addLayout(vbox_right)

        layout.addLayout(hlayout)
        self.central_widget.setLayout(layout)

    def add_job(self):
        name, ok = QInputDialog.getText(self, "New Job", "Enter job name:")
        if not ok or not name:
            return
        job = Job(name, working_path='', input_path='')
        self.project.jobs.append(job)
        self.job_list.addItem(name)
        self.job_list.setCurrentRow(self.job_list.count() - 1)
        self.job_list.item(self.job_list.count() - 1).setSelected(True)

    def on_job_double_clicked(self, item):
        index = self.job_list.row(item)
        if 0 <= index < len(self.project.jobs):
            job = self.project.jobs[index]
            self.show_job_config_dialog(job)

    def show_job_config_dialog(self, job):
        job_action = ActionConfig("Job", {
            'name': job.name,
            'working_path': job.working_path,
            'input_path': job.input_path
        })
        dialog = ActionConfigDialog(job_action, self)
        if dialog.exec():
            job.name = job_action.params['name']
            job.working_path = job_action.params['working_path']
            job.input_path = job_action.params['input_path']
            current_row = self.job_list.currentRow()
            if current_row >= 0:
                self.job_list.item(current_row).setText(job.name)

    def run_job(self):
        current_index = self.job_list.currentRow()
        if current_index < 0:
            QMessageBox.warning(self, "No Job Selected", "Please select a job first.")
            return
        if current_index >= 0:
            print("run: " + self.project.jobs[current_index].name)

    def run_all_jobs(self):
        for job in self.project.jobs:
            print("run: " + job.name)

    def add_action(self):
        from PySide6.QtWidgets import QInputDialog

        current_index = self.job_list.currentRow()
        if current_index < 0:
            QMessageBox.warning(self, "No Job Selected", "Please select a job first.")
            return
        type_name = self.action_selector.currentText()
        name, ok = QInputDialog.getText(self, "New Action", "Enter action name:")
        if not ok or not name:
            return
        params = {'name': name}
        action = ActionConfig(type_name, params)
        self.project.jobs[current_index].actions.append(action)
        self.action_list.addItem(self.action_text(action))

    def show_action_config_dialog(self, action):
        dialog = ActionConfigDialog(action, self)
        if dialog.exec():
            current_job_index = self.job_list.currentRow()
            self.on_job_selected(current_job_index)

    def update_delete_buttons_state(self):
        has_job_selected = len(self.job_list.selectedItems()) > 0
        has_action_selected = len(self.action_list.selectedItems()) > 0
        self.delete_job_button.setEnabled(has_job_selected)
        self.delete_action_button.setEnabled(has_action_selected)
        if has_action_selected and has_job_selected:
            job_index = self.job_list.currentRow()
            action_index = self.action_list.currentRow()
            job = self.project.jobs[job_index]
            action_counter = -1
            current_action = None
            is_sub_action = False
            for action in job.actions:
                action_counter += 1
                if action_counter == action_index:
                    current_action = action
                    break
                if action.type_name == COMBO_ACTIONS:
                    for sub_action in action.sub_actions:
                        action_counter += 1
                        if action_counter == action_index:
                            current_action = sub_action
                            is_sub_action = True
                            break
                    if current_action:
                        break
            enable_sub_actions = (current_action and not is_sub_action and current_action.type_name == COMBO_ACTIONS)
            self.sub_action_selector.setEnabled(enable_sub_actions)
            self.add_sub_action_button.setEnabled(enable_sub_actions)
            if is_sub_action:
                self.delete_action_button.setText("Delete Sub-action")
            else:
                self.delete_action_button.setText("Delete Action")
        else:
            self.sub_action_selector.setEnabled(False)
            self.add_sub_action_button.setEnabled(False)
            self.delete_action_button.setText("Delete Action")

    def delete_job(self):
        current_index = self.job_list.currentRow()
        if 0 <= current_index < len(self.project.jobs):
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Are you sure you want to delete job '{self.project.jobs[current_index].name}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.job_list.takeItem(current_index)
                self.project.jobs.pop(current_index)
                self.action_list.clear()

    def action_text(self, action, is_sub_action=False):
        txt = "    " + action.type_name if is_sub_action else action.type_name
        if "name" in action.params.keys() and action.params["name"] != '':
            txt += ": " + action.params["name"]
        return txt

    def on_job_selected(self, index):
        self.action_list.clear()
        if 0 <= index < len(self.project.jobs):
            job = self.project.jobs[index]
            for action in job.actions:
                self.action_list.addItem(self.action_text(action))
                if action.type_name == COMBO_ACTIONS:
                    for sub_action in action.sub_actions:
                        self.action_list.addItem(self.action_text(sub_action, is_sub_action=True))

    def add_sub_action(self):
        current_job_index = self.job_list.currentRow()
        current_action_index = self.action_list.currentRow()
        if (current_job_index < 0 or current_action_index < 0 or current_job_index >= len(self.project.jobs)):
            return
        job = self.project.jobs[current_job_index]
        action = None
        action_counter = -1
        for i, act in enumerate(job.actions):
            action_counter += 1
            if action_counter == current_action_index:
                action = act
                break
            if act.type_name == COMBO_ACTIONS:
                action_counter += len(act.sub_actions)
        if not action or action.type_name != COMBO_ACTIONS:
            return

        type_name = self.sub_action_selector.currentText()
        name, ok = QInputDialog.getText(self, "New Sub-Action", "Enter sub-action name:")
        if not ok or not name:
            return
        params = {'name': name}
        sub_action = ActionConfig(type_name, params)
        action.sub_actions.append(sub_action)
        self.on_job_selected(current_job_index)
        self.action_list.setCurrentRow(current_action_index)

    def on_action_double_clicked(self, item):
        job_index = self.job_list.currentRow()
        if 0 <= job_index < len(self.project.jobs):
            job = self.project.jobs[job_index]
            action_index = self.action_list.row(item)
            action_counter = -1
            current_action = None
            is_sub_action = False
            for action in job.actions:
                action_counter += 1
                if action_counter == action_index:
                    current_action = action
                    break
                if action.type_name == COMBO_ACTIONS:
                    for sub_action in action.sub_actions:
                        action_counter += 1
                        if action_counter == action_index:
                            current_action = sub_action
                            is_sub_action = True
                            break
                    if current_action:
                        break
            if current_action:
                if is_sub_action:
                    self.show_action_config_dialog(current_action)
                else:
                    if current_action.type_name == COMBO_ACTIONS:
                        self.sub_action_selector.setEnabled(True)
                        self.add_sub_action_button.setEnabled(True)
                    else:
                        self.sub_action_selector.setEnabled(False)
                        self.add_sub_action_button.setEnabled(False)
                    self.show_action_config_dialog(current_action)

    def delete_action(self):
        job_index = self.job_list.currentRow()
        action_index = self.action_list.currentRow()
        if (0 <= job_index < len(self.project.jobs)) and (0 <= action_index < self.action_list.count()):
            job = self.project.jobs[job_index]
            action_counter = -1
            current_action = None
            is_sub_action = False
            parent_action = None
            sub_action_index = -1
            for action in job.actions:
                action_counter += 1
                if action_counter == action_index:
                    current_action = action
                    break
                if action.type_name == COMBO_ACTIONS:
                    for i, sub_action in enumerate(action.sub_actions):
                        action_counter += 1
                        if action_counter == action_index:
                            current_action = sub_action
                            is_sub_action = True
                            parent_action = action
                            sub_action_index = i
                            break
                    if current_action:
                        break
            if current_action:
                reply = QMessageBox.question(
                    self,
                    "Confirm Delete",
                    f"Are you sure you want to delete action '{self.action_text(current_action, is_sub_action)}'?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    if is_sub_action:
                        parent_action.sub_actions.pop(sub_action_index)
                    else:
                        job.actions.pop(action_counter)
                    self.on_job_selected(job_index)
