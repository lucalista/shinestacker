# pylint: disable=C0114, C0116
import os
import sys
import platform
from .. config.config import config

if not config.DISABLE_TQDM:
    from tqdm import tqdm
    from tqdm.notebook import tqdm_notebook


def check_path_exists(path):
    if not os.path.exists(path):
        raise RuntimeError('Path does not exist: ' + path)


def make_tqdm_bar(name, size, ncols=80):
    if not config.DISABLE_TQDM:
        if config.JUPYTER_NOTEBOOK:
            tbar = tqdm_notebook(desc=name, total=size)
        else:
            tbar = tqdm(desc=name, total=size, ncols=ncols)
        return tbar
    return None


def get_app_base_path():
    sep = '\\' if (platform.system() == 'Windows') else '/'
    if getattr(sys, 'frozen', False):
        path = os.path.dirname(os.path.realpath(sys.executable))
        dirs = path.split(sep)
        last = -1
        for i in range(len(dirs) - 1, -1, -1):
            if dirs[i] == 'shinestacker':
                last = i
                break
        path = sep.join(dirs if last == 1 else dirs[:last + 1])
    elif __file__:
        path = sep.join(os.path.dirname(os.path.abspath(__file__)).split(sep)[:-3])
    return path


def running_under_windows() -> bool:
    return platform.system().lower() == 'windows'


def running_under_macos() -> bool:
    return platform.system().lower() == "darwin"


def running_under_linux() -> bool:
    return platform.system().lower() == 'linux'
