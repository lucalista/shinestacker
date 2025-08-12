import numpy as np


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

    def sort_layers(self, order):
        master_index = -1
        master_label = None
        master_layer = None
        for i, label in enumerate(self.layer_labels):
            if label.lower() == "master":
                master_index = i
                master_label = self.layer_labels.pop(i)
                master_layer = self.layer_stack[i]
                self.layer_stack = np.delete(self.layer_stack, i, axis=0)
                break
        if order == 'asc':
            self.sorted_indices = sorted(range(len(self.layer_labels)),
                                         key=lambda i: self.layer_labels[i].lower())
        elif order == 'desc':
            self.sorted_indices = sorted(range(len(self.layer_labels)),
                                         key=lambda i: self.layer_labels[i].lower(),
                                         reverse=True)
        else:
            raise ValueError(f"Invalid sorting order: {order}")
        self.layer_labels = [self.layer_labels[i] for i in self.sorted_indices]
        self.layer_stack = self.layer_stack[self.sorted_indices]
        if master_index != -1:
            self.layer_labels.insert(0, master_label)
            self.layer_stack = np.insert(self.layer_stack, 0, master_layer, axis=0)
            self.master_layer = master_layer.copy()
            self.master_layer.setflags(write=True)
        if self.current_layer_idx >= self.number_of_layers():
            self.current_layer_idx = self.number_of_layers() - 1
