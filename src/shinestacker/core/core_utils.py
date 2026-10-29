# pylint: disable=C0114, C0116, E0602, W0718
import os
import sys
import platform
import matplotlib
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
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def running_under_windows() -> bool:
    return platform.system().lower() == 'windows'


def running_under_macos() -> bool:
    return platform.system().lower() == "darwin"


def running_under_linux() -> bool:
    return platform.system().lower() == 'linux'


def external_process_env():
    """Environment for launching external programs (image viewer, file manager).

    A PyInstaller bundle points LD_LIBRARY_PATH (DYLD_LIBRARY_PATH on macOS)
    and some Qt variables at its own _internal directory. Child processes
    inherit them, so e.g. a KDE/GNOME image viewer started via xdg-open loads
    the bundled Qt libraries and plugins instead of the system ones and fails.
    Restore the values PyInstaller saved in *_ORIG and drop every other
    variable that points into the bundle.
    """
    env = dict(os.environ)
    if not getattr(sys, 'frozen', False):
        return env
    for var in ('LD_LIBRARY_PATH', 'DYLD_LIBRARY_PATH'):
        orig = env.pop(var + '_ORIG', None)
        if orig is not None:
            env[var] = orig
        else:
            env.pop(var, None)
    bundle_dir = getattr(sys, '_MEIPASS', None)
    if bundle_dir:
        for key in list(env):
            if key != 'PATH' and bundle_dir in env[key]:
                del env[key]
    return env


def make_chunks(ll, max_size):
    return [ll[i:i + max_size] for i in range(0, len(ll), max_size)]


def setup_matplotlib_mode():
    try:
        __IPYTHON__ # noqa
    except Exception:
        matplotlib.use('agg')
    matplotlib.pyplot.set_loglevel("warning")
    matplotlib.rcParams['pdf.fonttype'] = 42
