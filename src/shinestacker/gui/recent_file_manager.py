import os
from .. config.settings import StdPathFile


class RecentFileManager(StdPathFile):
    def __init__(self, filename, max_entries=10):
        super().__init__(filename)
        self.max_entries = max_entries

    def get_files(self):
        file_path = self.get_file_path()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                files = [line.strip() for line in f.readlines()]
                return [f for f in files if f and os.path.exists(f)]
        except (FileNotFoundError, IOError):
            return []

    def get_files_with_display_names(self):
        files = self.get_files()
        basename_count = {}
        for file_path in files:
            basename = os.path.basename(file_path)
            basename_count[basename] = basename_count.get(basename, 0) + 1
        result = {}
        for file_path in files:
            basename = os.path.basename(file_path)
            if basename_count[basename] == 1:
                result[file_path] = basename
            else:
                parent_dir = os.path.basename(os.path.dirname(file_path))
                result[file_path] = f"{basename} ({parent_dir})"
                if list(result.values()).count(result[file_path]) > 1:
                    path_components = file_path.split(os.sep)
                    for i in range(2, min(5, len(path_components))):
                        display_name = os.sep.join(path_components[-i:])
                        if sum(1 for f in files
                                if os.sep.join(os.path.normpath(f).split(os.sep)[-i:]) ==
                                display_name) == 1:
                            result[file_path] = display_name
                            break
                    else:
                        if len(file_path) > 50:
                            result[file_path] = "..." + file_path[-47:]
                        else:
                            result[file_path] = file_path
        return result

    def add_file(self, file_path):
        file_path = os.path.abspath(file_path)
        recent_files = self.get_files()
        if file_path in recent_files:
            recent_files.remove(file_path)
        recent_files.insert(0, file_path)
        recent_files = recent_files[:self.max_entries]
        self._save_files(recent_files)

    def remove_file(self, file_path):
        file_path = os.path.normpath(file_path)
        recent_files = self.get_files()
        if file_path in recent_files:
            recent_files.remove(file_path)
        self._save_files(recent_files)

    def _save_files(self, files):
        file_path = self.get_file_path()
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(files))
        except IOError as e:
            raise e

    def clear(self):
        self._save_files([])
