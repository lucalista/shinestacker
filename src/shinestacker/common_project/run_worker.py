# pylint: disable=C0114, C0115, C0116, E0611, R0913, R0917
from PySide6.QtCore import Signal
from .. config.constants import constants
from .. gui.qt_plot_manager import QtPlotManager
from .. gui.gui_logging import LogWorker
from .. gui.project_converter import ProjectConverter

COLOR_RED = "FF5050"
COLOR_BLUE = "5050FF"


class RunWorker(LogWorker):
    before_action_signal = Signal(int, str)
    after_action_signal = Signal(int, str)
    step_counts_signal = Signal(int, str, int)
    begin_steps_signal = Signal(int, str)
    end_steps_signal = Signal(int, str)
    after_step_signal = Signal(int, str, int)
    save_plot_signal = Signal(int, str, str, str, str)
    open_app_signal = Signal(int, str, str, str)
    run_completed_signal = Signal(int, str)
    run_stopped_signal = Signal(int, str)
    run_failed_signal = Signal(int, str)
    add_status_box_signal = Signal(str)
    add_frame_signal = Signal(str, str, int)
    set_total_actions_signal = Signal(str, str, int)
    update_frame_status_signal = Signal(str, str, int)

    def __init__(self, id_str):
        LogWorker.__init__(self)
        self.id_str = id_str
        self.status = constants.STATUS_RUNNING
        self.callbacks = {
            constants.CALLBACK_BEFORE_ACTION: self.before_action,
            constants.CALLBACK_AFTER_ACTION: self.after_action,
            constants.CALLBACK_STEP_COUNTS: self.step_counts,
            constants.CALLBACK_BEGIN_STEPS: self.begin_steps,
            constants.CALLBACK_END_STEPS: self.end_steps,
            constants.CALLBACK_AFTER_STEP: self.after_step,
            constants.CALLBACK_CHECK_RUNNING: self.check_running,
            constants.CALLBACK_SAVE_PLOT: self.save_plot,
            constants.CALLBACK_OPEN_APP: self.open_app,
            constants.CALLBACK_ADD_STATUS_BOX: self.add_status_box,
            constants.CALLBACK_ADD_FRAME: self.add_frame,
            constants.CALLBACKS_SET_TOTAL_ACTIONS: self.set_total_actions,
            constants.CALLBACK_UPDATE_FRAME_STATUS: self.update_frame_status
        }
        self.tag = ""
        self.plot_manager = QtPlotManager(self)
        self.name = ''

    def before_action(self, run_id, name):
        self.name = name
        self.before_action_signal.emit(run_id, name)

    def after_action(self, run_id, name):
        self.after_action_signal.emit(run_id, name)

    def step_counts(self, run_id, name, steps):
        self.step_counts_signal.emit(run_id, name, steps)

    def begin_steps(self, run_id, name):
        self.begin_steps_signal.emit(run_id, name)

    def end_steps(self, run_id, name):
        self.end_steps_signal.emit(run_id, name)

    def after_step(self, run_id, name, step):
        self.after_step_signal.emit(run_id, name, step)

    def save_plot(self, run_id, module_name, caption, path, tag="_default"):
        self.save_plot_signal.emit(run_id, module_name, caption, path, tag)

    def open_app(self, run_id, name, app, path):
        self.open_app_signal.emit(run_id, name, app, path)

    def add_status_box(self, module_name):
        self.add_status_box_signal.emit(module_name)

    def add_frame(self, module_name, filename, total_actions):
        self.add_frame_signal.emit(module_name, filename, total_actions)

    def update_frame_status(self, module_name, filename, status_id):
        self.update_frame_status_signal.emit(module_name, filename, status_id)

    def set_total_actions(self, module_name, filename, status_id):
        self.set_total_actions_signal.emit(module_name, filename, status_id)

    def check_running(self, _run_id, _name):
        return self.status == constants.STATUS_RUNNING

    def run(self):
        # pylint: disable=line-too-long
        self.status_signal.emit(f"{self.tag} running...", constants.RUN_ONGOING, "", 0)
        self.html_signal.emit(f'''
        <div style="margin: 2px 0; font-family: {constants.LOG_FONTS_STR};">
        <span style="color: #{COLOR_BLUE}; font-style: italic; font-weight: bold;">{self.tag} begins</span>
        </div>
        ''') # noqa
        status, error_message = self.do_run()
        run_id = int(self.id_str.split('_')[-1])
        if status == constants.RUN_COMPLETED:
            message = f"{self.tag} ended successfully"
            self.run_completed_signal.emit(run_id, self.name)
            color = COLOR_BLUE
        elif status == constants.RUN_STOPPED:
            message = f"{self.tag} stopped"
            color = COLOR_RED
            self.run_stopped_signal.emit(run_id, self.name)
        elif status == constants.RUN_FAILED:
            message = f"{self.tag} failed"
            color = COLOR_RED
            self.run_failed_signal.emit(run_id, self.name)
        else:
            message = ''
            color = "#000000"
        self.html_signal.emit(f'''
        <div style="margin: 2px 0; font-family: {constants.LOG_FONTS_STR};">
        <span style="color: #{color}; font-style: italic; font-weight: bold;">{message}</span>
        </div>
        ''')
        # pylint: enable=line-too-long
        self.end_signal.emit(status, self.id_str, message)
        self.status_signal.emit(message, status, error_message, 0)

    def stop(self):
        self.status = constants.STATUS_STOPPED
        self.wait()


class JobLogWorker(RunWorker):
    def __init__(self, job, id_str):
        super().__init__(id_str)
        self.job = job
        self.tag = "Job"

    def do_run(self):
        converter = ProjectConverter(self.plot_manager)
        return converter.run_job(self.job, self.id_str, self.callbacks)


class ProjectLogWorker(RunWorker):
    def __init__(self, project, id_str):
        super().__init__(id_str)
        self.project = project
        self.tag = "Project"

    def do_run(self):
        converter = ProjectConverter(self.plot_manager)
        return converter.run_project(self.project, self.id_str, self.callbacks)
