from shinestacker.retouch.layer_collection import LayerCollection


def test_layer_collection():
    print("Starting comprehensive tests for LayerCollection...")
    lc = LayerCollection()
    assert lc.master_layer is None
    assert lc.master_layer_copy is None
    assert lc.layer_stack is None
    assert lc.layer_labels is None
    assert lc.current_layer_idx == 0
    print("✓ Initial state passed")
    lc.layer_stack = []
    assert lc.number_of_layers() == 0, "Empty stack should have 0 layers"
    lc.layer_stack = ["layer1", "layer2"]
    assert lc.number_of_layers() == 2, "Stack should have 2 layers"
    print("✓ Layer counting passed")
    lc.current_layer_idx = 0
    assert lc.valid_current_layer_idx()
    lc.current_layer_idx = 1
    assert lc.valid_current_layer_idx()
    lc.current_layer_idx = -1
    assert not lc.valid_current_layer_idx()
    lc.current_layer_idx = 3
    assert not lc.valid_current_layer_idx()
    print("✓ Index validation passed")
    lc.layer_stack = ["A", "B", "C"]
    lc.current_layer_idx = 1
    assert lc.current_layer() == "B"
    lc.current_layer_idx = 5
    cl = lc.current_layer()
    assert cl is None, "Current layer should be None"
    print("✓ Current layer raises IndexError on invalid index")
    lc.layer_stack = []
    lc.current_layer_idx = 0
    cl = lc.current_layer()
    assert cl is None, "Current layer should be None"
    print("✓ Empty stack handling passed")

    class MockLayer:
        def copy(self):
            return "Copy of layer"

    lc.master_layer = MockLayer()
    lc.copy_master_layer()
    assert lc.master_layer_copy == "Copy of layer"
    print("✓ Master layer copy passed")
    lc = LayerCollection()
    try:
        lc.number_of_layers()
        assert False, "Should raise TypeError on None stack"
    except TypeError:
        print("✓ None stack handling in number_of_layers()")
    cl = lc.current_layer()
    assert cl is None, "Current layer should be None"
    print("✓ None stack handling in current_layer()")
    try:
        lc.copy_master_layer()
        assert False, "Should raise AttributeError on None master"
    except AttributeError:
        print("✓ None master layer handling in copy_master_layer()")
    print("✓✓ All tests passed successfully!")


if __name__ == '__main__':
    test_layer_collection()
