# pylint: disable=R0904, R0917, R0913, R0903, W0212
class ProjectHandler:
    def __init__(self, project):
        self._project = project

    def project(self):
        return self._project

    def set_project(self, project):
        self._project.copy_from(project)

    def project_jobs(self):
        return self._project.jobs

    def num_project_jobs(self):
        return len(self.project_jobs())

    def add_job_to_project(self, job):
        self._project.jobs.append(job)

    def is_valid_job_index(self, index):
        return 0 <= index < self.num_project_jobs()

    def project_job(self, index):
        return self._project.jobs[index] if self.is_valid_job_index(index) else None

    def is_valid_index_in(self, a, index):
        return False if a is None else 0 <= index < len(a.sub_actions)

    def project_action(self, job_index, action_index):
        job = self.project_job(job_index)
        if job is None:
            return None
        return job.sub_actions[action_index] \
            if self.is_valid_index_in(job, action_index) else None

    def project_subaction(self, job_index, action_index, subaction_index):
        action = self.project_action(job_index, action_index)
        if action is None:
            return None
        return action.sub_actions[subaction_index] \
            if self.is_valid_index_in(action, subaction_index) else None

    def project_element(self, job_index, action_index=-1, subaction_index=-1):
        if job_index < 0:
            return None
        if action_index < 0:
            return self.project_job(job_index)
        if subaction_index < 0:
            return self.project_action(job_index, action_index)
        return self.project_subaction(job_index, action_index, subaction_index)

    def project_container(self, job_index=-1, action_index=-1):
        if job_index < 0:
            return self.project().jobs
        if action_index < 0:
            return self.project_job(job_index).sub_actions
        return self.project_action(job_index, action_index).sub_actions

    def valid_indices(self, job_index, action_index=-1, subaction_index=-1):
        job = self.project_job(job_index)
        if job is None:
            return False
        if action_index == -1:
            return True
        if not self.is_valid_index_in(job, action_index):
            return False
        if subaction_index == -1:
            return True
        action = job.sub_actions[action_index]
        return self.is_valid_index_in(action, subaction_index)
