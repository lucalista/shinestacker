# pylint: disable=C0114, C0116
import os
from ..config.config import config

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
