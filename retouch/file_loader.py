import numpy as np
import tifffile
from psdtags import PsdChannelId
from PySide6.QtCore import QThread, Signal
from algorithms.multilayer import read_multilayer_tiff


class FileLoader(QThread):
    finished = Signal(object, object, object)
    error = Signal(str)

    def __init__(self, path):
        super().__init__()
        self.path = path

    def run(self):
        try:
            current_stack, current_labels = self.load_tiff_stack(self.path)
            if current_stack is None or len(current_stack) == 0:
                self.error.emit("Empty or invalid stack")
                return
            master_indices = [i for i, label in enumerate(current_labels) if label.lower() == "master"]
            master_index = -1 if len(master_indices) == 0 else master_indices[0]
            if master_index == -1:
                master_layer = current_stack[0].copy()
            else:
                current_labels.pop(master_index)
                master_layer = current_stack[master_index].copy()
                indices = list(range(len(current_stack)))
                indices.remove(master_index)
                current_stack = current_stack[indices]
            master_layer.setflags(write=True)
            if current_labels is None:
                current_labels = [f"Layer {i + 1}" for i in range(len(current_stack))]
            self.finished.emit(current_stack, current_labels, master_layer)
        except Exception as e:
            self.error.emit(f"Error loading file: {str(e)}")

    def load_tiff_stack(self, path):
        try:
            psd_data = read_multilayer_tiff(path)
            layers = []
            labels = []
            for layer in reversed(psd_data.layers.layers):
                channels = {}
                for channel in layer.channels:
                    channels[channel.channelid] = channel.data
                if PsdChannelId.CHANNEL0 in channels:
                    img = np.stack([
                        channels[PsdChannelId.CHANNEL0],
                        channels[PsdChannelId.CHANNEL1],
                        channels[PsdChannelId.CHANNEL2]
                    ], axis=-1)
                    layers.append(img)
                    labels.append(layer.name)
            if layers:
                stack = np.array(layers)
                if labels:
                    master_indices = [i for i, label in enumerate(labels) if label.lower() == "master"]
                    if master_indices:
                        master_index = master_indices[0]
                        master_label = labels.pop(master_index)
                        master_layer = stack[master_index]
                        stack = np.delete(stack, master_index, axis=0)
                        labels.insert(0, master_label)
                        stack = np.insert(stack, 0, master_layer, axis=0)
                    return stack, labels
                return stack, labels
        except Exception:
            try:
                stack = tifffile.imread(path)
                if stack.ndim == 3:
                    return stack, None
                return None, None
            except Exception:
                return None, None
