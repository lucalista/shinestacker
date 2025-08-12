class FilterManager:
    def __init__(self, editor):
        self.editor = editor
        self.filters = {}

    def register_filter(self, name, filter_class):
        self.filters[name] = filter_class(self.editor)

    def get_filter(self, name):
        return self.filters.get(name)

    def apply(self, name, **kwargs):
        if name in self.filters:
            self.filters[name].run_with_preview(**kwargs)
