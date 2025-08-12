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
        return self.current_layer_idx >= 0 or self.current_layer_idx < self.number_of_layers()

    def current_layer(self):
        return self.layer_stack[self.current_layer_idx] if self.valid_current_layer_idx() else None

    def copy_master_layer(self):
        self.master_layer_copy = self.master_layer.copy()
