# pylint: disable=R1716, R0904


class SelectionState:
    def __init__(self, job_index=-1, action_index=-1, subaction_index=-1):
        self.set_indices(job_index, action_index, subaction_index)

    def set_indices(self, job_idx=-1, action_idx=-1, subaction_idx=-1):
        self.job_index = job_idx
        self.action_index = action_idx
        self.subaction_index = subaction_idx

    def reset(self):
        self.set_indices(-1, -1, -1)

    def is_job_selected(self):
        return self.job_index >= 0 and self.action_index < 0

    def is_action_selected(self):
        return self.job_index >= 0 and self.action_index >= 0 and self.subaction_index < 0

    def is_subaction_selected(self):
        return self.job_index >= 0 and self.action_index >= 0 and self.subaction_index >= 0

    def is_valid(self):
        return self.job_index >= 0

    def type(self):
        if self.job_index < 0:
            return ''
        if self.action_index < 0:
            return 'job'
        if self.subaction_index < 0:
            return 'action'
        return 'subaction'

    def to_tuple(self):
        return self.get_indices()

    def from_tuple(self, indices_tuple):
        if len(indices_tuple) >= 3:
            self.set_indices(*indices_tuple[:3])

    def copy_from(self, other_state):
        self.set_indices(
            other_state.job_index, other_state.action_index, other_state.subaction_index)

    def get_indices(self):
        return (self.job_index, self.action_index, self.subaction_index)

    def copy(self):
        return SelectionState(self.job_index, self.action_index, self.subaction_index)
