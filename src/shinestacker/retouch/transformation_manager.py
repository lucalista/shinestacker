# pylint: disable=W0718
import traceback
import cv2
from .. config.gui_constants import gui_constants
from .layer_collection import LayerCollectionHandler


class TransfromationManager(LayerCollectionHandler):
    def __init__(self, editor):
        super().__init__(editor.layer_collection)
        self.editor = editor

    def transform(self, transf_func, label, undoable=True):
        if self.has_no_master_layer():
            return
        if undoable:
            try:
                undo = self.editor.undo_manager
                undo.set_paint_area(0, 1, 0, 1)
                undo.save_undo_state(self.editor.master_layer(), label)
            except Exception:
                traceback.print_exc()
        self.set_master_layer(transf_func(self.master_layer()))
        self.set_layer_stack([transf_func(layer) for layer in self.layer_stack()])
        self.copy_master_layer()
        self.editor.image_viewer.update_master_display()
        self.editor.image_viewer.update_current_display()
        self.editor.display_manager.update_thumbnails()
        self.editor.mark_as_modified()

    def rotate_90_cw(self, undoable=True):
        self.transform(lambda img: cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE),
                       gui_constants.ROTATE_90_CW_LABEL, undoable)

    def rotate_90_ccw(self, undoable=True):
        self.transform(lambda img: cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE),
                       gui_constants.ROTATE_90_CCW_LABEL, undoable)

    def rotate_180(self, undoable=True):
        self.transform(lambda img: cv2.rotate(img, cv2.ROTATE_180),
                       gui_constants.ROTATE_180_LABEL, undoable)
