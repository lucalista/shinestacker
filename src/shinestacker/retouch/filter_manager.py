# pylint: disable=C0114, C0115, C0116
class FilterManager:
    def __init__(self, editor):
        self.editor = editor
        self.filters = {}

    def register_filter(self, name, filter_class):
        self.filters[name] = filter_class(name, self.editor)

    def apply(self, name, **kwargs):
        if name in self.filters:
            self.filters[name].run_with_preview(**kwargs)
