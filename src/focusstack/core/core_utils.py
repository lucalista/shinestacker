import os
import sys
import platform
from focusstack.config.config import config

if not config.DISABLE_TQDM:
    from tqdm import tqdm
    from tqdm.notebook import tqdm_notebook


def check_path_exists(path):
    if not os.path.exists(path):
        raise Exception('Path does not exist: ' + path)


def make_tqdm_bar(name, size, ncols=80):
    if not config.DISABLE_TQDM:
        if config.JUPYTER_NOTEBOOK:
            bar = tqdm_notebook(desc=name, total=size)
        else:
            bar = tqdm(desc=name, total=size, ncols=ncols)
        return bar
    else:
        return None


def get_app_base_path():
    if getattr(sys, 'frozen', False):
        path = os.path.dirname(os.path.realpath(sys.executable))
    elif __file__:
        sep = '\\' if (platform.system() == 'Windows') else '/'
        path = sep.join(os.path.dirname(os.path.abspath(__file__)).split(sep)[:-3])
    return path


def running_under_windows() -> bool:
    return platform.system().lower() == 'windows'


def running_under_macos() -> bool:
    return platform.system().lower() == "darwin"


def running_under_linux() -> bool:
    return platform.system().lower() == 'linux'
