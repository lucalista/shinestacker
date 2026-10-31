# pylint: disable=R0903, R0903, W0718
import os
import gc
import logging
import traceback
import threading
from abc import ABC, abstractmethod
import matplotlib.pyplot as plt
from .. config.config import config


class PlotManager(ABC):
    @abstractmethod
    def save_plot(self, filename, fig, tag="_default"):
        pass


class DirectPlotManager(PlotManager):
    def __init__(self):
        self.lock = threading.Lock()

    def save_plot(self, filename, fig, tag="_default"):
        logger = logging.getLogger(__name__)
        logger.debug(msg=f"Saving plot to: {filename}")
        dir_path = os.path.dirname(filename)
        if dir_path and not os.path.isdir(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        try:
            with self.lock:
                original_level = logging.getLogger().level
                if original_level < logging.WARNING:
                    logging.getLogger().setLevel(logging.WARNING)
                if fig is None:
                    fig = plt.gcf()
                fig.savefig(filename, dpi=150, bbox_inches='tight')
                if original_level < logging.WARNING:
                    logging.getLogger().setLevel(original_level)
                if config.JUPYTER_NOTEBOOK:
                    try:
                        plt.show()
                    except Exception as e:
                        traceback.print_exc()
                        logger.warning(msg=f"Could not display plot in Jupyter: {e}")
                plt.close(fig)
        except Exception as e:
            logger.error(msg=f"Failed to save plot to {filename}: {e}")
            try:
                plt.close(fig)
            except Exception:
                traceback.print_exc()
            raise
        finally:
            gc.collect()
        return True
