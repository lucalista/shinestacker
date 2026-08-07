# pylint: disable=C0114, C0115, C0116, E0611, W0718, R0903, E0611, R0911
import os
import json
import traceback
import copy
import jsonpickle
import numpy as np
from PySide6.QtCore import QStandardPaths
from .. config.defaults import DEFAULTS

CURRENT_SETTINGS_FILE_VERSION = 1


class StdPathFile:
    def __init__(self, filename):
        self._config_dir = None
        self.filename = filename

    def get_config_dir(self):
        if self._config_dir is None:
            config_dir = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
            if not config_dir:
                if os.name == 'nt':
                    config_dir = os.path.join(os.environ.get('APPDATA', ''), 'ShineStacker')
                elif os.name == 'posix':
                    config_dir = os.path.expanduser('~/.config/shinestacker')
                else:
                    config_dir = os.path.join(os.path.expanduser('~'), '.shinestacker')
            os.makedirs(config_dir, exist_ok=True)
            self._config_dir = config_dir
        return self._config_dir

    def get_file_path(self):
        return os.path.join(self.get_config_dir(), self.filename)


class Settings(StdPathFile):
    _instance = None
    _observers = []

    def __init__(self, filename):
        if Settings._instance is not None:
            raise RuntimeError("Settings is a singleton.")
        super().__init__(filename)
        self.defaults = self._deep_copy_defaults()
        self.settings = self._deep_copy_defaults()
        file_path = self.get_file_path()
        if os.path.isfile(file_path):
            try:
                with open(file_path, 'r', encoding="utf-8") as file:
                    json_data = json.load(file)
                    file_settings = json_data['settings']
                    self._deep_merge_settings(file_settings)
            except Exception:
                traceback.print_exc()
                print(f"Can't read file from path {file_path}. Default settings ignored.")

    def _deep_copy_defaults(self):
        defaults_copy = copy.deepcopy(DEFAULTS)
        return self._convert_to_python_types(defaults_copy)

    def _convert_to_python_types(self, obj):
        try:
            numpy_available = True
        except ImportError:
            numpy_available = False
        if numpy_available:
            if hasattr(obj, 'item') and hasattr(obj, 'dtype'):
                return obj.item()
            if isinstance(obj, np.bool_):
                return bool(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
        if isinstance(obj, dict):
            return {k: self._convert_to_python_types(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._convert_to_python_types(item) for item in obj]
        if isinstance(obj, tuple):
            return tuple(self._convert_to_python_types(item) for item in obj)
        return obj

    def _deep_merge_settings(self, file_settings):
        for key, value in file_settings.items():
            if key in self.settings:
                if isinstance(value, dict) and isinstance(self.settings[key], dict):
                    for sub_key, sub_value in value.items():
                        if sub_key in self.settings[key]:
                            self.settings[key][sub_key] = sub_value
                else:
                    self.settings[key] = value

    def _get_diff_from_defaults(self):
        def diff_dict(current, default):
            diff = {}
            for key, value in current.items():
                if key in default:
                    if isinstance(value, dict) and isinstance(default[key], dict):
                        nested_diff = diff_dict(value, default[key])
                        if nested_diff:
                            diff[key] = nested_diff
                    elif value != default[key]:
                        diff[key] = value
            return diff
        return diff_dict(self.settings, self.defaults)

    @classmethod
    def instance(cls, filename="shinestacker-settings.txt"):
        if cls._instance is None:
            cls._instance = cls(filename)
        return cls._instance

    @classmethod
    def add_observer(cls, observer):
        cls._observers.append(observer)

    def set(self, key, value):
        self.settings[key] = value

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def update(self):
        try:
            config_dir = self.get_config_dir()
            os.makedirs(config_dir, exist_ok=True)
            diff_settings = self._get_diff_from_defaults()
            serializable_diff = self._convert_to_python_types(diff_settings)
            json_data = {
                'version': CURRENT_SETTINGS_FILE_VERSION,
                'settings': serializable_diff
            }
            json_obj = jsonpickle.encode(json_data, keys=True)
            with open(self.get_file_path(), 'w', encoding="utf-8") as f:
                f.write(json_obj)
        except IOError as e:
            raise e
        for observer in Settings._observers:
            observer.update(self.settings)

    @classmethod
    def reset_instance_only_for_testing(cls):
        cls._instance = None
