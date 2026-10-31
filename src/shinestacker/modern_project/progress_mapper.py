import os
from .. gui.project_model import get_action_output_path
from .. common_project.selection_state import SelectionState


class ProgressMapper:
    def __init__(self):
        self.mapping = {}

    def build_mapping(self, project, job_indices=None):
        self.mapping = {}
        if job_indices is None:
            jobs_to_check = enumerate(project.jobs)
        else:
            jobs_to_check = [(idx, project.jobs[idx]) for idx in job_indices]
        for job_idx, job in jobs_to_check:
            for action_idx, action in enumerate(job.sub_actions):
                output_path = get_action_output_path(action)[0]
                if output_path:
                    norm_path = os.path.normpath(output_path)
                    if norm_path not in self.mapping:
                        self.mapping[norm_path] = (job_idx, action_idx, -1)
                for subaction_idx, subaction in enumerate(action.sub_actions):
                    sub_output_path = get_action_output_path(subaction)[0]
                    if sub_output_path:
                        sub_norm_path = os.path.normpath(sub_output_path)
                        if sub_norm_path not in self.mapping:
                            self.mapping[sub_norm_path] = (job_idx, action_idx, subaction_idx)
                    sub_name = subaction.params.get('name', '')
                    if sub_name and sub_name not in self.mapping:
                        self.mapping[sub_name] = (job_idx, action_idx, subaction_idx)
        return self.mapping

    def get_state(self, module_name):
        indices = self.mapping.get(module_name)
        if indices:
            return SelectionState(*indices)
        return None
