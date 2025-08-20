# pylint: disable=E1101, C0114, C0115, C0116, E0611, W0718, R0903
import traceback
import cv2
from PySide6.QtCore import QThread, Signal
from .. algorithms.utils import read_img, validate_image, get_img_metadata
from .. algorithms.exif import get_exif, write_image_with_exif_data
from .. algorithms.multilayer import write_multilayer_tiff_from_images
from .layer_collection import LayerCollectionHandler


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
            traceback.print_tb(e.__traceback__)
            self.error.emit(str(e))


class IOManager(LayerCollectionHandler):
    def __init__(self, layer_collection):
        super().__init__(layer_collection)
        self.exif_path = ''
        self.exif_data = None

    def import_frames(self, file_paths):
        stack = []
        labels = []
        master = None
        shape, dtype = get_img_metadata(self.master_layer())
        for path in file_paths:
            try:
                label = path.split("/")[-1].split(".")[0]
                img = cv2.cvtColor(read_img(path), cv2.COLOR_BGR2RGB)
                if shape is not None and dtype is not None:
                    validate_image(img, shape, dtype)
                else:
                    shape, dtype = get_img_metadata(img)
                label_x = label
                i = 0
                while label_x in labels:
                    i += 1
                    label_x = f"{label} ({i})"
                labels.append(label_x)
                stack.append(img)
                if master is None:
                    master = img.copy()
            except Exception as e:
                raise RuntimeError(f"Error loading file: {path}.\n{str(e)}") from e
        return stack, labels, master

    def save_master(self, path):
        img = cv2.cvtColor(self.master_layer(), cv2.COLOR_RGB2BGR)
        write_image_with_exif_data(self.exif_data, img, path)

    def set_exif_data(self, path):
        self.exif_path = path
        self.exif_data = get_exif(path)
