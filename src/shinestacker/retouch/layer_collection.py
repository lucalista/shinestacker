# pylint: disable=C0114, C0115, C0116, R0904
import numpy as np


class LayerCollection:
    def __init__(self):
        self.master_layer = None
        self.master_layer_copy = None
        self.layer_stack = None
        self.layer_labels = []
        self.current_layer_idx = 0
        self.sorted_indices = None

    def reset(self):
        self.master_layer = None
        self.master_layer_copy = None
        self.layer_stack = None
        self.layer_labels = []
        self.current_layer_idx = 0
        self.sorted_indices = None

    def has_master_layer(self):
        return self.master_layer is not None

    def has_no_master_layer(self):
        return self.master_layer is None

    def has_master_layer_copy(self):
        return self.master_layer_copy is not None

    def has_no_master_layer_copy(self):
        return self.master_layer_copy is None

    def number_of_layers(self):
        if self.layer_stack is None:
            return 0
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

    def restore_master_layer(self):
        self.master_layer = self.master_layer_copy.copy()

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
            label_lower = label.lower()
            if "master" in label_lower or "stack" in label_lower:
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


class LayerCollectionHandler:
    def __init__(self, layer_collection=None):
        self.layer_collection = layer_collection

    def set_layer_collection(self, coll):
        self.layer_collection = coll

    def master_layer(self):
        return self.layer_collection.master_layer

    def current_layer(self):
        return self.layer_collection.current_layer()

    def layer_stack(self):
        return self.layer_collection.layer_stack

    def layer_labels(self):
        return self.layer_collection.layer_labels

    def set_layer_label(self, i, val):
        self.layer_collection.set_layer_label(i, val)

    def set_layer_labels(self, labels):
        self.layer_collection.set_layer_labels(labels)

    def current_layer_idx(self):
        return self.layer_collection.current_layer_idx

    def has_no_master_layer(self):
        return self.layer_collection.has_no_master_layer()

    def has_master_layer(self):
        return self.layer_collection.has_master_layer()

    def set_layer_stack(self, stk):
        self.layer_collection.set_layer_stack(stk)

    def set_master_layer(self, img):
        self.layer_collection.set_master_layer(img)

    def add_layer_label(self, label):
        self.layer_collection.add_layer_label(label)

    def add_layer(self, img):
        self.layer_collection.add_layer(img)

    def master_layer_copy(self):
        return self.layer_collection.master_layer_copy

    def copy_master_layer(self):
        self.layer_collection.copy_master_layer()

    def restore_master_layer(self):
        self.layer_collection.restore_master_layer()

    def set_current_layer_idx(self, idx):
        self.layer_collection.set_current_layer_idx(idx)

    def sort_layers(self, order):
        self.layer_collection.sort_layers(order)

    def number_of_layers(self):
        return self.layer_collection.number_of_layers()

    def valid_current_layer_idx(self):
        return self.layer_collection.valid_current_layer_idx()
