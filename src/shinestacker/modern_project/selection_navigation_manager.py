# pylint: disable=E0611, R0912
from PySide6.QtCore import QObject
from .. common_project.project_handler import ProjectHandler


class SelectionNavigationManager(ProjectHandler, QObject):
    def __init__(self, project, selection_state, select_callback):
        ProjectHandler.__init__(self, project)
        QObject.__init__(self)
        self.selection_state = selection_state
        self.select = select_callback

    def handle_key_navigation(self, key):
        if not self.jobs_exist():
            return False
        if key in ("up", "left"):
            self.select_previous_widget()
            return True
        if key in ("down", "right"):
            self.select_next_widget()
            return True
        if key == "home":
            self._select_first_job()
            return True
        if key == "end":
            self._select_last_job()
            return True
        return False

    def select_next_widget(self):
        if self.selection_state.is_job_selected():
            if self._get_action_count(self.selection_state.job_index) > 0:
                self.select('action', self.selection_state.job_index, 0)
        elif self.selection_state.is_action_selected():
            if self._get_subaction_count(self.selection_state.job_index,
                                         self.selection_state.action_index) > 0:
                self.select('subaction', self.selection_state.job_index,
                            self.selection_state.action_index, 0)
            else:
                if self.selection_state.action_index + 1 < self._get_action_count(
                        self.selection_state.job_index):
                    self.select('action', self.selection_state.job_index,
                                self.selection_state.action_index + 1)
                else:
                    if self.selection_state.job_index + 1 < self.num_project_jobs():
                        next_job_index = self.selection_state.job_index + 1
                        self.select('job', next_job_index)
        elif self.selection_state.is_subaction_selected():
            if self.selection_state.subaction_index + 1 < self._get_subaction_count(
                    self.selection_state.job_index, self.selection_state.action_index):
                self.select('subaction', self.selection_state.job_index,
                            self.selection_state.action_index,
                            self.selection_state.subaction_index + 1)
            else:
                if self.selection_state.action_index + 1 < self._get_action_count(
                        self.selection_state.job_index):
                    next_action_index = self.selection_state.action_index + 1
                    if self._get_subaction_count(self.selection_state.job_index,
                                                 next_action_index) > 0:
                        self.select('subaction', self.selection_state.job_index,
                                    next_action_index, 0)
                    else:
                        self.select('action', self.selection_state.job_index, next_action_index)
                else:
                    if self.selection_state.job_index + 1 < self.num_project_jobs():
                        next_job_index = self.selection_state.job_index + 1
                        self.select('job', next_job_index)

    def select_previous_widget(self):
        if self.selection_state.is_subaction_selected():
            if self.selection_state.subaction_index > 0:
                self.select('subaction',
                            self.selection_state.job_index,
                            self.selection_state.action_index,
                            self.selection_state.subaction_index - 1)
            else:
                self.select('action',
                            self.selection_state.job_index,
                            self.selection_state.action_index)
        elif self.selection_state.is_action_selected():
            if self.selection_state.action_index > 0:
                prev_action_index = self.selection_state.action_index - 1
                if self._has_subactions_in_action(
                        self.selection_state.job_index, prev_action_index):
                    last_subaction_index = self._get_subaction_count(
                        self.selection_state.job_index, prev_action_index) - 1
                    self.select('subaction',
                                self.selection_state.job_index,
                                prev_action_index,
                                last_subaction_index)
                else:
                    self.select('action',
                                self.selection_state.job_index,
                                prev_action_index)
            else:
                self.select('job', self.selection_state.job_index)
        elif self.selection_state.is_job_selected():
            if self.selection_state.job_index > 0:
                prev_job_index = self.selection_state.job_index - 1
                if self._has_actions_in_job(prev_job_index):
                    last_action_index = self._get_action_count(prev_job_index) - 1
                    if self._has_subactions_in_action(prev_job_index, last_action_index):
                        last_subaction_index = self._get_subaction_count(
                            prev_job_index, last_action_index) - 1
                        self.select('subaction',
                                    prev_job_index,
                                    last_action_index,
                                    last_subaction_index)
                    else:
                        self.select('action',
                                    prev_job_index,
                                    last_action_index)
                else:
                    self.select('job', prev_job_index)

    def _select_first_job(self):
        if self.num_project_jobs() > 0:
            self.select('job', 0)

    def _select_last_job(self):
        if self.num_project_jobs() > 0:
            self.select('job', self.num_project_jobs() - 1)

    def _select_first_action_in_job(self, job_index):
        self.select('action', job_index, 0)

    def _select_first_subaction_in_action(self, job_index, action_index):
        self.select('subaction', job_index, action_index, 0)

    def _has_actions_in_job(self, job_index):
        return self._get_action_count(job_index) > 0

    def _has_subactions_in_action(self, job_index, action_index):
        return self._get_subaction_count(job_index, action_index) > 0

    def _is_valid_job_index(self, job_index):
        return 0 <= job_index < self.num_project_jobs()

    def _get_action_count(self, job_index):
        if self._is_valid_job_index(job_index):
            job = self.project_job(job_index)
            return len(job.sub_actions) if hasattr(job, 'sub_actions') else 0
        return 0

    def _get_subaction_count(self, job_index, action_index):
        if self._is_valid_job_index(job_index):
            job = self.project_job(job_index)
            if 0 <= action_index < len(job.sub_actions):
                action = job.sub_actions[action_index]
                return len(action.sub_actions) if hasattr(action, 'sub_actions') else 0
        return 0

    def jobs_exist(self):
        return self.num_project_jobs() > 0

    def restore_selection(self, old_state):
        if not old_state.is_valid():
            if self.jobs_exist():
                self.select('job', 0)
            return
        job_idx = old_state.job_index
        if not self._is_valid_job_index(job_idx):
            if self.jobs_exist():
                self.select('job', 0)
            return
        if old_state.is_job_selected():
            self.select('job', job_idx)
        elif old_state.is_action_selected():
            action_idx = old_state.action_index
            if 0 <= action_idx < self._get_action_count(job_idx):
                self.select('action', job_idx, action_idx)
            elif self._get_action_count(job_idx) > 0:
                self.select('action', job_idx, 0)
            else:
                self.select('job', job_idx)
        elif old_state.is_subaction_selected():
            action_idx = old_state.action_index
            subaction_idx = old_state.subaction_index
            if 0 <= action_idx < self._get_action_count(job_idx):
                if 0 <= subaction_idx < self._get_subaction_count(job_idx, action_idx):
                    self.select('subaction', job_idx, action_idx, subaction_idx)
                elif self._get_subaction_count(job_idx, action_idx) > 0:
                    self.select('subaction', job_idx, action_idx, 0)
                else:
                    self.select('action', job_idx, action_idx)
            elif self._get_action_count(job_idx) > 0:
                self.select('action', job_idx, 0)
            else:
                self.select('job', job_idx)
