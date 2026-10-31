# pylint: disable=E0611, E1101, W0718, R0903, R0914

# import time
import os
import traceback
import cv2
from PySide6.QtCore import QThread, Signal
from .. algorithms.utils import read_img, validate_image, get_img_metadata
from .. algorithms.multilayer import write_multilayer_tiff_from_images


class FileMultilayerSaver(QThread):
    finished = Signal()
    error = Signal(str)

    def __init__(self, images_dict, path, exif_path=None):
        super().__init__()
        self.images_dict = images_dict
        self.path = path
        self.exif_path = exif_path

    def run(self):
        try:
            write_multilayer_tiff_from_images(
                self.images_dict, self.path, exif_path=self.exif_path)
            self.finished.emit()
        except Exception as e:
            traceback.print_exc()
            self.error.emit(str(e))


class FrameImporter(QThread):
    finished = Signal(object, object, object)
    error = Signal(str)
    progress = Signal(int, str)

    def __init__(self, file_paths, master_layer):
        super().__init__()
        self.file_paths = file_paths
        self.master_layer = master_layer

    def run(self):
        try:
            stack = []
            labels = []
            master = None
            current_master = self.master_layer
            shape, dtype = None, None
            if current_master is not None:
                shape, dtype = get_img_metadata(current_master)
            total_files = len(self.file_paths)
            for i, path in enumerate(self.file_paths):
                progress_percent = int((i / total_files) * 100)
                self.progress.emit(progress_percent, os.path.basename(path))
                try:
                    label = path.split("/")[-1].split(".")[0]
                    img = cv2.cvtColor(read_img(path), cv2.COLOR_BGR2RGB)
                    if shape is not None and dtype is not None:
                        validate_image(img, shape, dtype)
                    else:
                        shape, dtype = get_img_metadata(img)
                    label_x = label
                    counter = 0
                    while label_x in labels:
                        counter += 1
                        label_x = f"{label} ({counter})"
                    labels.append(label_x)
                    stack.append(img)
                    if master is None:
                        master = img.copy()
                except Exception as e:
                    raise RuntimeError(f"Error loading file: {path}.\n{str(e)}") from e
            self.progress.emit(100, "Complete")
            self.finished.emit(stack, labels, master)
        except Exception as e:
            self.error.emit(str(e))
