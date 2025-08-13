import cv2
from .. core.exceptions import ShapeError, BitDepthError
from .. algorithms.utils import read_img, validate_image, get_img_metadata
from .. algorithms.exif import get_exif, write_image_with_exif_data
from .. algorithms.multilayer import write_multilayer_tiff_from_images


class IOManager:
    def __init__(self, layer_collection):
        layer_collection.add_to(self)
        self.current_file_path = ''
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
            except ShapeError as e:
                raise ShapeError(f"All files must have the same shape.\n{str(e)}")
            except BitDepthError as e:
                raise BitDepthError(f"All files must have the same bit depth.\n{str(e)}")
            except Exception as e:
                raise RuntimeError(f"Error loading file: {path}.\n{str(e)}")
        return stack, labels, master

    def save_multilayer(self, path):
        master_layer = {'Master': self.master_layer()}
        individual_layers = {label: image for label, image in zip(
            self.layer_labels(), self.layer_stack())}
        write_multilayer_tiff_from_images({**master_layer, **individual_layers}, path, exif_path=self.exif_path)

    def save_master(self, path):
        img = cv2.cvtColor(self.master_layer(), cv2.COLOR_RGB2BGR)
        write_image_with_exif_data(self.exif_data, img, path)

    def set_exif_data(self, path):
        self.exif_path = path
        self.exif_data = get_exif(path)
