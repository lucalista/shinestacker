from shinestacker.retouch.layer_collection import LayerCollection
import numpy as np
import pytest


class MockLayer:
    def __init__(self, data):
        self.data = data

    def copy(self):
        return MockLayer(self.data)

    def setflags(self, write=True):
        """Dummy method to match numpy array interface"""
        pass

    def __eq__(self, other):
        return self.data == other.data if isinstance(other, MockLayer) else False


def test_initial_state():
    lc = LayerCollection()
    assert lc.master_layer is None
    assert lc.master_layer_copy is None
    assert lc.layer_stack is None
    assert lc.layer_labels == []
    assert lc.current_layer_idx == 0


def test_number_of_layers():
    lc = LayerCollection()
    lc.layer_stack = []
    assert lc.number_of_layers() == 0
    lc.layer_stack = ["layer1", "layer2"]
    assert lc.number_of_layers() == 2
    with pytest.raises(TypeError):
        lc.layer_stack = None
        lc.number_of_layers()


def test_valid_current_layer_idx():
    lc = LayerCollection()
    lc.layer_stack = ["A", "B", "C"]
    lc.current_layer_idx = 0
    assert lc.valid_current_layer_idx()
    lc.current_layer_idx = 1
    assert lc.valid_current_layer_idx()
    lc.current_layer_idx = -1
    assert not lc.valid_current_layer_idx()
    lc.current_layer_idx = 3
    assert not lc.valid_current_layer_idx()


def test_current_layer():
    lc = LayerCollection()
    lc.layer_stack = ["A", "B", "C"]
    lc.current_layer_idx = 1
    assert lc.current_layer() == "B"
    lc.current_layer_idx = 5
    assert lc.current_layer() is None
    lc.layer_stack = []
    lc.current_layer_idx = 0
    assert lc.current_layer() is None
    lc.layer_stack = None
    assert lc.current_layer() is None


def test_master_layer_handling():
    lc = LayerCollection()
    assert lc.has_no_master_layer()
    assert not lc.has_master_layer()
    layer = MockLayer("data")
    lc.set_master_layer(layer)
    assert lc.master_layer == layer
    assert lc.has_master_layer()
    assert not lc.has_no_master_layer()


def test_master_layer_copy():
    lc = LayerCollection()
    with pytest.raises(AttributeError):
        lc.copy_master_layer()
    layer = MockLayer("data")
    lc.set_master_layer(layer)
    lc.copy_master_layer()
    assert lc.master_layer_copy == layer
    assert lc.master_layer_copy is not layer


def test_layer_management():
    lc = LayerCollection()
    lc.layer_stack = np.array([], dtype=object)
    layer1 = MockLayer("L1")
    layer2 = MockLayer("L2")
    lc.add_layer(layer1)
    lc.add_layer(layer2)
    assert lc.number_of_layers() == 2
    assert lc.layer_stack[0] == layer1
    assert lc.layer_stack[1] == layer2
    lc.add_layer_label("Label1")
    lc.add_layer_label("Label2")
    assert lc.layer_labels == ["Label1", "Label2"]
    lc.set_layer_label(0, "NewLabel")
    assert lc.layer_labels == ["NewLabel", "Label2"]
    lc.set_layer_labels(["A", "B"])
    assert lc.layer_labels == ["A", "B"]


def test_sort_layers_ascending_with_master():
    lc = LayerCollection()
    master = MockLayer("master")
    layerB = MockLayer("B")
    layerA = MockLayer("A")
    lc.layer_labels = ["Master", "B", "A"]
    lc.layer_stack = np.array([master, layerB, layerA], dtype=object)
    lc.set_master_layer(master)
    lc.sort_layers('asc')
    assert lc.layer_labels == ["Master", "A", "B"]
    assert lc.layer_stack[0] == master
    assert lc.layer_stack[1] == layerA
    assert lc.layer_stack[2] == layerB
    assert lc.master_layer == master


def test_sort_layers_descending_with_master():
    lc = LayerCollection()
    master = MockLayer("master")
    layerA = MockLayer("A")
    layerC = MockLayer("C")
    layerB = MockLayer("B")
    lc.layer_labels = ["Master", "A", "C", "B"]
    lc.layer_stack = np.array([master, layerA, layerC, layerB], dtype=object)
    lc.sort_layers('desc')
    assert lc.layer_labels == ["Master", "C", "B", "A"]
    assert lc.layer_stack[0] == master
    assert lc.layer_stack[1] == layerC
    assert lc.layer_stack[2] == layerB
    assert lc.layer_stack[3] == layerA


def test_sort_layers_ascending_without_master():
    lc = LayerCollection()
    layerC = MockLayer("C")
    layerA = MockLayer("A")
    layerB = MockLayer("B")
    lc.layer_labels = ["C", "A", "B"]
    lc.layer_stack = np.array([layerC, layerA, layerB], dtype=object)
    lc.sort_layers('asc')
    assert lc.layer_labels == ["A", "B", "C"]
    assert lc.layer_stack[0] == layerA
    assert lc.layer_stack[1] == layerB
    assert lc.layer_stack[2] == layerC


def test_sort_layers_descending_without_master():
    lc = LayerCollection()
    layerA = MockLayer("A")
    layerC = MockLayer("C")
    layerB = MockLayer("B")
    lc.layer_labels = ["A", "C", "B"]
    lc.layer_stack = np.array([layerA, layerC, layerB], dtype=object)
    lc.sort_layers('desc')
    assert lc.layer_labels == ["C", "B", "A"]
    assert lc.layer_stack[0] == layerC
    assert lc.layer_stack[1] == layerB
    assert lc.layer_stack[2] == layerA


def test_sort_layers_current_index_adjustment():
    lc = LayerCollection()
    master = MockLayer("master")
    layerA = MockLayer("A")
    layerB = MockLayer("B")
    lc.layer_labels = ["Master", "B", "A"]
    lc.layer_stack = np.array([master, layerB, layerA], dtype=object)
    lc.current_layer_idx = 3  # Out-of-bounds index
    lc.sort_layers('asc')
    assert lc.current_layer_idx == 2  # Should be adjusted to max valid index
    lc.current_layer_idx = 1
    lc.sort_layers('asc')
    assert lc.current_layer_idx == 1  # Should remain valid


def test_invalid_sort_order():
    lc = LayerCollection()
    lc.layer_labels = ["A", "B"]
    lc.layer_stack = np.array([MockLayer("A"), MockLayer("B")], dtype=object)
    with pytest.raises(ValueError, match="Invalid sorting order: invalid"):
        lc.sort_layers('invalid')


def test_add_to_method():
    lc = LayerCollection()
    obj = type('TestObj', (), {})()
    lc.add_to(obj)
    assert obj.layer_collection == lc
    assert obj.master_layer() == lc.master_layer
    assert obj.current_layer() == lc.current_layer()
    assert obj.layer_stack() == lc.layer_stack
    assert obj.layer_labels() == lc.layer_labels
    lc.layer_labels = ["Test"]
    assert obj.layer_labels() == ["Test"]
    obj.set_layer_label(0, "Updated")
    assert lc.layer_labels == ["Updated"]
