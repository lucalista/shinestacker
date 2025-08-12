class LayerCollection:
    def __init__(self):
        self.master_layer = None
        self.master_layer_copy = None
        self.layer_stack = None
        self.layer_labels = None
        self.current_layer_idx = 0

    def number_of_layers(self):
        return len(self.layer_stack)

    def valid_current_layer_idx(self):
        return 0 <= self.current_layer_idx < self.number_of_layers()

    def current_layer(self):
        if self.layer_stack is not None and self.valid_current_layer_idx():
            return self.layer_stack[self.current_layer_idx]
        return None

    def copy_master_layer(self):
        self.master_layer_copy = self.master_layer.copy()
