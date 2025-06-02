from PySide6.QtWidgets import (
    QMainWindow, QWidget, QPushButton, QVBoxLayout, QListWidget, QHBoxLayout,
    QFileDialog, QLabel, QComboBox, QMessageBox, QInputDialog, 
    QDialog, QFormLayout, QLineEdit)
from gui.project_model import Project, Job, ActionConfig

SUB_ACTION_TYPES = ["MaskNoise", "Vignetting", "AlignFrames", "BalanceFrames"]

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
        self.action_selector.addItems([
            "NoiseDetection",
            "Actions",
            "FocusStackBunch",
            "FocusStack",
            "MultiLayer"
        ])

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


    def on_job_selected(self, index):
        self.action_list.clear()
        if 0 <= index < len(self.project.jobs):
            job = self.project.jobs[index]
            for action in job.actions:
                self.action_list.addItem(self.action_text(action))

    def on_job_double_clicked(self, item):
        index = self.job_list.row(item)
        if 0 <= index < len(self.project.jobs):
            job = self.project.jobs[index]
            self.show_job_config_dialog(job)

    def show_job_config_dialog(self, job):
        dialog = QDialog(self)
        dialog.setWindowTitle("Configure Job")
        layout = QFormLayout()
    
        name_edit = QLineEdit(job.name)
        layout.addRow("Job Name:", name_edit)
    
        working_path_edit = QLineEdit(job.working_path)
        working_path_button = QPushButton("Browse...")
        
        input_path_edit = QLineEdit(job.input_path)
        input_path_button = QPushButton("Browse...")
    
        def browse_working_path():
            path = QFileDialog.getExistingDirectory(self, "Select Input Directory")
            if path:
                working_path_edit.setText(path)
        def browse_input_path():
            path = QFileDialog.getExistingDirectory(self, "Select Input Directory")
            if path:
                input_path_edit.setText(path)
        
        working_path_button.clicked.connect(browse_working_path)
        input_path_button.clicked.connect(browse_input_path)

        working_path_layout = QHBoxLayout()
        working_path_layout.addWidget(working_path_edit)
        working_path_layout.addWidget(working_path_button)
        layout.addRow("Working Path:", working_path_layout)
        
        input_path_layout = QHBoxLayout()
        input_path_layout.addWidget(input_path_edit)
        input_path_layout.addWidget(input_path_button)
        layout.addRow("Input Path:", input_path_layout)
        
        button_box = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        button_box.addWidget(ok_button)
        button_box.addWidget(cancel_button)
        layout.addRow(button_box)

        def save_and_close():
            job.name = name_edit.text()
            job.working_path = working_path_edit.text()
            job.input_path = input_path_edit.text()
            current_row = self.job_list.currentRow()
            if current_row >= 0:
                self.job_list.item(current_row).setText(job.name)
            dialog.accept()
        
        ok_button.clicked.connect(save_and_close)
        cancel_button.clicked.connect(dialog.reject)

        dialog.setLayout(layout)
        dialog.exec()

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

    def action_text(self, action):
        txt = action.type_name
        if "name" in action.params.keys() and action.params["name"] != '':
            txt += ": " + action.params["name"]
        return txt
    
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
        
    def on_action_double_clicked(self, item):
        job_index = self.job_list.currentRow()
        if 0 <= job_index < len(self.project.jobs):
            job = self.project.jobs[job_index]
            action_index = self.action_list.row(item)
            
            # Trova l'azione corrispondente
            action_counter = -1
            current_action = None
            is_sub_action = False
            
            for action in job.actions:
                action_counter += 1
                if action_counter == action_index:
                    current_action = action
                    break
                if action.type_name == "Actions":
                    for sub_action in action.sub_actions:
                        action_counter += 1
                        if action_counter == action_index:
                            current_action = sub_action
                            is_sub_action = True
                            break
                    if current_action:
                        break
            if current_action:
                self.show_action_config_dialog(current_action)
            self.update_delete_buttons_state()
    
    def show_action_config_dialog(self, action):       
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Configure {action.type_name}")
        layout = QFormLayout()
        
        if 'name' not in action.params.keys():
            action.params['name'] = ''
        
        name_edit = QLineEdit(action.params['name'])
        layout.addRow(f"{action.type_name} name:", name_edit)
        
        button_box = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        button_box.addWidget(ok_button)
        button_box.addWidget(cancel_button)
        layout.addRow(button_box)
    
        def save_and_close():
            action.params['name'] = name_edit.text()
            current_job_index = self.job_list.currentRow()
            self.on_job_selected(current_job_index)
            dialog.accept()
        
        ok_button.clicked.connect(save_and_close)
        cancel_button.clicked.connect(dialog.reject)
    
        dialog.setLayout(layout)
        dialog.exec()

    def update_delete_buttons_state(self):
        has_job_selected = len(self.job_list.selectedItems()) > 0
        has_action_selected = len(self.action_list.selectedItems()) > 0
        
        self.delete_job_button.setEnabled(has_job_selected)
        self.delete_action_button.setEnabled(has_action_selected)
        
        if has_action_selected and has_job_selected:
            job_index = self.job_list.currentRow()
            action_index = self.action_list.currentRow()
            job = self.project.jobs[job_index]
            
            # Trova l'azione corrispondente
            action_counter = -1
            current_action = None
            is_sub_action = False
            
            for action in job.actions:
                action_counter += 1
                if action_counter == action_index:
                    current_action = action
                    break
                if action.type_name == "Actions":
                    for sub_action in action.sub_actions:
                        action_counter += 1
                        if action_counter == action_index:
                            current_action = sub_action
                            is_sub_action = True
                            break
                    if current_action:
                        break
            enable_sub_actions = (current_action and 
                                not is_sub_action and 
                                current_action.type_name == "Actions")
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
                self, 
                "Confirm Delete",
                f"Are you sure you want to delete job '{self.project.jobs[current_index].name}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.job_list.takeItem(current_index)
                self.project.jobs.pop(current_index)
                self.action_list.clear()
    
    def delete_action(self):
        job_index = self.job_list.currentRow()
        action_index = self.action_list.currentRow()
        if (0 <= job_index < len(self.project.jobs)) and (0 <= action_index < len(self.project.jobs[job_index].actions)):
            action = self.project.jobs[job_index].actions[action_index]
            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                f"Are you sure you want to delete action '{self.action_text(action)}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Rimuovi dalla lista e dal job
                self.action_list.takeItem(action_index)
                self.project.jobs[job_index].actions.pop(action_index)
    
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
                if action.type_name == "Actions":
                    for sub_action in action.sub_actions:
                        self.action_list.addItem(self.action_text(sub_action, is_sub_action=True))
    
    def add_sub_action(self):
        current_job_index = self.job_list.currentRow()
        current_action_index = self.action_list.currentRow()
        
        if (current_job_index < 0 or current_action_index < 0 or 
            current_job_index >= len(self.project.jobs)):
            return
        
        job = self.project.jobs[current_job_index]
        action = None
        
        action_counter = -1
        for i, act in enumerate(job.actions):
            action_counter += 1
            if action_counter == current_action_index:
                action = act
                break
            if act.type_name == "Actions":
                action_counter += len(act.sub_actions)
        
        if not action or action.type_name != "Actions":
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
            parent_action = None
            
            for action in job.actions:
                action_counter += 1
                if action_counter == action_index:
                    current_action = action
                    break
                if action.type_name == "Actions":
                    for sub_action in action.sub_actions:
                        action_counter += 1
                        if action_counter == action_index:
                            current_action = sub_action
                            is_sub_action = True
                            parent_action = action
                            break
                    if current_action:
                        break
            
            if current_action:
                if is_sub_action:
                    self.show_action_config_dialog(current_action)
                else:
                    if current_action.type_name == "Actions":
                        # Abilita/disabilita i controlli per sub-actions
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
                if action.type_name == "Actions":
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
