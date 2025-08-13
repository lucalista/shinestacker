import numpy as np


class LayerCollection:
    def add_to(self, obj):
        obj.layer_collection = self
        obj.master_layer = lambda: obj.layer_collection.master_layer
        obj.current_layer = lambda: obj.layer_collection.current_layer()
        obj.layer_stack = lambda: obj.layer_collection.layer_stack
        obj.layer_labels = lambda: obj.layer_collection.layer_labels
        obj.set_layer_label = lambda i, val: obj.layer_collection.set_layer_label(i, val)
        obj.set_layer_labels = lambda labels: obj.layer_collection.set_layer_labels(labels)
        obj.current_layer_idx = lambda: obj.layer_collection.current_layer_idx
        obj.has_no_master_layer = lambda: obj.layer_collection.has_no_master_layer()
        obj.has_master_layer = lambda: obj.layer_collection.has_master_layer()
        obj.set_layer_stack = lambda stk: obj.layer_collection.set_layer_stack(stk)
        obj.set_master_layer = lambda img: obj.layer_collection.set_master_layer(img)
        obj.add_layer_label = lambda label: obj.layer_collection.add_layer_label(label)
        obj.add_layer = lambda img: obj.layer_collection.add_layer(img)
        obj.master_layer_copy = lambda: obj.layer_collection.master_layer_copy
        obj.copy_master_layer = lambda: obj.layer_collection.copy_master_layer()
        obj.set_current_layer_idx = lambda idx: obj.layer_collection.set_current_layer_idx(idx)
        obj.sort_layers = lambda order: obj.layer_collection.sort_layers(order)
        obj.number_of_layers = lambda: obj.layer_collection.number_of_layers()
        obj.valid_current_layer_idx = lambda: obj.layer_collection.valid_current_layer_idx()

    def __init__(self):
        self.reset()

    def reset(self):
        self.master_layer = None
        self.master_layer_copy = None
        self.layer_stack = None
        self.layer_labels = []
        self.current_layer_idx = 0

    def has_master_layer(self):
        return self.master_layer is not None

    def has_no_master_layer(self):
        return self.master_layer is None

    def has_master_layer_copy(self):
        return self.master_layer_copy is not None

    def has_no_master_layer_copy(self):
        return self.master_layer_copy is None

    def number_of_layers(self):
        return len(self.layer_stack)

    def layer_label(self, i):
        return self.layer_labels[i]

    def set_layer_label(self, i, val):
        self.layer_labels[i] = val

    def set_layer_labels(self, labels):
        self.layer_labels = labels

    def set_layer_stack(self, stk):
        self.layer_stack = stk

    def set_current_layer_idx(self, idx):
        self.current_layer_idx = idx

    def valid_current_layer_idx(self):
        return 0 <= self.current_layer_idx < self.number_of_layers()

    def current_layer(self):
        if self.layer_stack is not None and self.valid_current_layer_idx():
            return self.layer_stack[self.current_layer_idx]
        return None

    def set_master_layer(self, img):
        self.master_layer = img

    def copy_master_layer(self):
        self.master_layer_copy = self.master_layer.copy()

    def add_layer_label(self, label):
        if self.layer_labels is None:
            self.layer_labels = [label]
        else:
            self.layer_labels.append(label)

    def add_layer(self, img):
        self.layer_stack = np.append(self.layer_stack, [img], axis=0)

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
