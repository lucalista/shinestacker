# pylint: disable=R0913, R0917
class FilterManager:
    def __init__(self, editor):
        self.editor = editor
        self.image_viewer = editor.image_viewer
        self.layer_collection = editor.layer_collection
        self.undo_manager = editor.undo_manager
        self.filters = {}

    def register_filter(self, name, filter_class,
                        update_master_thumbnail, mark_as_modified, filter_gui_set_enabled):
        filter_obj = filter_class(
            name, self.editor, self.image_viewer, self.layer_collection, self.undo_manager)
        self.filters[name] = filter_obj
        filter_obj.connect_signals(
            update_master_thumbnail, mark_as_modified, filter_gui_set_enabled)

    def apply(self, name, **kwargs):
        if name in self.filters:
            self.filters[name].run_with_preview(**kwargs)
