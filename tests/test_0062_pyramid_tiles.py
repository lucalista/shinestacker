import pytest
import numpy as np
import os
from unittest.mock import MagicMock, patch
from shinestacker.config.defaults import DEFAULTS
from shinestacker.algorithms.pyramid_tiles import PyramidTilesStack


@pytest.fixture
def example_images():
    image_dir = "examples/input/img-jpg/"
    filenames = [os.path.join(image_dir, f"000{i}.jpg") for i in range(3)]
    for f in filenames:
        if not os.path.exists(f):
            pytest.skip(f"Test image {f} not found")
    return filenames


def test_initialization():
    pts = PyramidTilesStack()
    assert pts.tile_size == DEFAULTS['pyramid_params']['tile_size']
    assert pts.n_tiled_layers == DEFAULTS['pyramid_params']['n_tiled_layers']
    assert pts.float_type == {
        'float-32': np.float32,
        'float-64': np.float64
    }.get(DEFAULTS['pyramid_params']['float_type'])


def test_temp_directory_creation():
    pts = PyramidTilesStack()
    assert os.path.exists(pts.temp_dir_path)
    assert pts.temp_dir_path is not None


def test_init_with_examples(example_images):
    pts = PyramidTilesStack()
    pts.print_message = MagicMock()
    pts.check_running = MagicMock()
    pts.init(example_images)
    assert pts.num_images() == len(example_images)
    assert pts.n_tiles > 0
    assert isinstance(pts.level_shapes, dict)


def test_process_single_image_with_mock(example_images):
    pts = PyramidTilesStack()
    pts.print_message = MagicMock()
    pts.check_running = MagicMock()
    pts._check_disk_space = MagicMock()
    pts.init(example_images[:1])
    mock_img = np.random.rand(100, 100, 3).astype(np.uint8)
    with patch.object(pts, 'single_image_laplacian') as mock_laplacian:
        mock_laplacian.return_value = [np.random.rand(50, 50, 3), np.random.rand(25, 25, 3)]
        level_count = pts.process_single_image(mock_img, 2, 0)
        assert level_count == 2
        assert 0 in pts.level_shapes
        assert len(pts.level_shapes[0]) == 2


def test_cleanup_temp_files():
    pts = PyramidTilesStack()
    pts.print_message = MagicMock()
    pts.temp_dir_manager = None
    pts.temp_dir_path = "/tmp/test_dir"
    with patch('shinestacker.algorithms.pyramid_tiles.glob.glob') as mock_glob, \
         patch('shinestacker.algorithms.pyramid_tiles.os.remove') as mock_remove:
        mock_glob.return_value = ['file1.npy', 'file2.npy']
        pts.cleanup_temp_files()
        assert mock_remove.call_count == 2


def test_safe_cleanup():
    pts = PyramidTilesStack()
    pts.print_message = MagicMock()
    pts.cleanup_temp_files = MagicMock()
    pts._safe_cleanup()
    pts.cleanup_temp_files.assert_called_once()


def test_check_disk_space_sufficient():
    pts = PyramidTilesStack()
    pts.print_message = MagicMock()
    with patch('shinestacker.algorithms.pyramid_tiles.shutil.disk_usage') as mock_disk:
        mock_disk.return_value = (100, 50, 50 * 1024**3)  # 50 GB free
        try:
            pts._check_disk_space()
        except Exception:
            pytest.fail("_check_disk_space raised unexpectedly when space was sufficient")


def test_check_disk_space_insufficient():
    pts = PyramidTilesStack()
    pts.print_message = MagicMock()
    with patch('shinestacker.algorithms.pyramid_tiles.shutil.disk_usage') as mock_disk:
        mock_disk.return_value = (100, 95, 4 * 1024**3)
        with pytest.raises(Exception) as exc_info:
            pts._check_disk_space()
        assert "critically low disk space during operation" in str(exc_info.value).lower()


def test_focus_stack_parallel_mock(example_images):
    pts = PyramidTilesStack()
    pts.print_message = MagicMock()
    pts.check_running = MagicMock()
    pts.process = MagicMock()
    pts.process.callback.return_value = None
    pts._check_disk_space = MagicMock()
    pts.single_image_laplacian = MagicMock(return_value=[np.random.rand(50, 50, 3)])
    pts.fuse_laplacian = MagicMock(return_value=np.random.rand(50, 50, 3))
    pts.get_fused_base = MagicMock(return_value=np.random.rand(50, 50, 3))
    pts.collapse = MagicMock(return_value=np.random.rand(100, 100, 3).astype(np.uint8))
    pts.init(example_images[:2])
    result = pts.focus_stack()
    assert result.shape == (100, 100, 3)
    assert result.dtype == np.uint8


def test_process_tile_method():
    pts = PyramidTilesStack()
    pts.print_message = MagicMock()
    pts.fuse_laplacian = MagicMock(return_value=np.ones((10, 10, 3), dtype=np.float32))
    mock_tile = np.random.rand(10, 10, 3).astype(np.float32)
    with patch.object(pts, 'load_level_tile', return_value=mock_tile):
        result = pts._process_tile(0, 3, [1, 1, 1], 0, 0, 100, 100)
        assert result.shape == (10, 10, 3)
        assert result.dtype == np.float32
        pts.fuse_laplacian.assert_called_once()


def test_total_steps():
    pts = PyramidTilesStack()
    pts.n_tiles = 10
    base_steps = pts.total_steps(5)
    assert base_steps == super(PyramidTilesStack, pts).total_steps(5) + 10


def test_num_threads_initialization():
    pts = PyramidTilesStack(max_threads=4)
    assert pts.num_threads <= 4
    assert pts.num_threads >= 1


def test_image_str_method():
    pts = PyramidTilesStack()
    pts.filenames = ['img1.jpg', 'img2.jpg', 'img3.jpg', 'img4.jpg', 'img5.jpg']
    result = pts.image_str(2)
    assert "3/5" in result


def test_process_tile_no_laplacians():
    pts = PyramidTilesStack()
    pts.print_message = MagicMock()
    pts.fuse_laplacian = MagicMock()
    result = pts._process_tile(0, 3, [0, 0, 0], 0, 0, 100, 100)
    assert result.shape == (100, 100, 3)
    assert result.dtype == np.float32
    assert np.all(result == 0)
    pts.fuse_laplacian.assert_not_called()


def test_fuse_pyramids_mock():
    pts = PyramidTilesStack()
    pts.print_message = MagicMock()
    pts.check_running = MagicMock()
    pts.after_step = MagicMock()
    pts.process = MagicMock()
    pts.process.callback.return_value = None
    pts._fuse_level_tiles_serial = MagicMock(return_value=(np.random.rand(50, 50, 3), 0))
    pts._fuse_level_tiles_parallel = MagicMock(return_value=(np.random.rand(50, 50, 3), 0))
    pts.load_level = MagicMock(return_value=np.random.rand(50, 50, 3))
    pts.fuse_laplacian = MagicMock(return_value=np.random.rand(50, 50, 3))
    pts.get_fused_base = MagicMock(return_value=np.random.rand(50, 50, 3))
    pts.filenames = ['img1.jpg', 'img2.jpg', 'img3.jpg']
    pts.level_shapes = {
        0: [(50, 50), (25, 25)],
        1: [(50, 50), (25, 25)],
        2: [(50, 50), (25, 25)]
    }
    all_level_counts = [2, 2, 2]
    result = pts.fuse_pyramids(all_level_counts)
    assert len(result) == 2
    assert all(isinstance(level, np.ndarray) for level in result)


def test_focus_stack_serial_mock(example_images):
    pts = PyramidTilesStack()
    pts.print_message = MagicMock()
    pts.check_running = MagicMock()
    pts.process = MagicMock()
    pts.process.callback.return_value = None
    pts._check_disk_space = MagicMock()
    pts.single_image_laplacian = MagicMock(return_value=[np.random.rand(50, 50, 3)])
    pts.fuse_laplacian = MagicMock(return_value=np.random.rand(50, 50, 3))
    pts.get_fused_base = MagicMock(return_value=np.random.rand(50, 50, 3))
    pts.collapse = MagicMock(return_value=np.random.rand(100, 100, 3).astype(np.uint8))
    pts.num_threads = 1  # Force serial processing
    pts.init(example_images[:1])
    result = pts.focus_stack()
    assert result.shape == (100, 100, 3)
    assert result.dtype == np.uint8


def test_load_level_tile_method():
    pts = PyramidTilesStack()
    pts.temp_dir_path = "/tmp/test_dir"
    mock_tile = np.random.rand(10, 10, 3)
    with patch('shinestacker.algorithms.pyramid_tiles.np.load', return_value=mock_tile):
        result = pts.load_level_tile(0, 1, 0, 0)
        assert np.array_equal(result, mock_tile)


def test_load_level_method():
    pts = PyramidTilesStack()
    pts.temp_dir_path = "/tmp/test_dir"
    mock_level = np.random.rand(50, 50, 3)
    with patch('shinestacker.algorithms.pyramid_tiles.np.load', return_value=mock_level):
        result = pts.load_level(0, 1)
        assert np.array_equal(result, mock_level)


def test_process_single_image_wrapper():
    pts = PyramidTilesStack()
    pts.print_message = MagicMock()
    pts.check_running = MagicMock()
    pts.process_single_image = MagicMock(return_value=3)
    mock_img = np.random.rand(100, 100, 3).astype(np.uint8)
    with patch('shinestacker.algorithms.pyramid_tiles.read_and_validate_img',
               return_value=mock_img):
        args = ('test.jpg', 0, 5)
        result = pts._process_single_image_wrapper(args)
        assert result == (0, 'test.jpg', 3)
        pts.process_single_image.assert_called_once_with(mock_img, pts.n_levels, 0)


def test_focus_stack_stop_exception(example_images):
    pts = PyramidTilesStack()
    pts.print_message = MagicMock()
    pts.process = MagicMock()
    pts.process.callback.return_value = None
    pts._check_disk_space = MagicMock()
    pts.check_running = MagicMock(side_effect=Exception("Stop requested"))
    pts.init(example_images[:1])
    with pytest.raises(Exception, match="Stop requested"):
        pts.focus_stack()


def test_min_free_space_gb_initialization():
    pts = PyramidTilesStack()
    assert hasattr(pts, 'min_free_space_gb')
    assert pts.min_free_space_gb == 5


def test_focus_stack_file_not_found():
    pts = PyramidTilesStack()
    pts.print_message = MagicMock()
    pts.process = MagicMock()
    pts.filenames = ['nonexistent1.jpg', 'nonexistent2.jpg']
    with pytest.raises(Exception):
        pts.focus_stack()


def test_cleanup_temp_files_with_exception():
    pts = PyramidTilesStack()
    pts.print_message = MagicMock()
    pts.temp_dir_manager = None
    pts.temp_dir_path = "/tmp/test_dir"
    with patch('shinestacker.algorithms.pyramid_tiles.glob.glob') as mock_glob, \
         patch('shinestacker.algorithms.pyramid_tiles.os.remove') as mock_remove:
        mock_glob.return_value = ['file1.npy', 'file2.npy']
        mock_remove.side_effect = [None, Exception("Permission denied")]
        pts.cleanup_temp_files()  # Should not raise despite one removal failing
        assert mock_remove.call_count == 2


def test_fuse_level_tiles_serial_missing_tile():
    pts = PyramidTilesStack()
    pts.print_message = MagicMock()
    pts.check_running = MagicMock()
    pts.after_step = MagicMock()
    pts.fuse_laplacian = MagicMock(return_value=np.ones((10, 10, 3), dtype=np.float32))
    pts.load_level_tile = MagicMock(side_effect=FileNotFoundError("Tile not found"))
    result, count = pts._fuse_level_tiles_serial(0, 3, [1, 1, 1], 100, 100, 0)
    assert result.shape == (100, 100, 3)
    assert np.all(result == 0)  # Should be zeros when no tiles are loaded
    pts.fuse_laplacian.assert_not_called()  # Should not try to fuse empty list


def test_fuse_level_tiles_parallel_exception():
    pts = PyramidTilesStack()
    pts.print_message = MagicMock()
    pts.check_running = MagicMock()
    pts.after_step = MagicMock()
    pts._process_tile = MagicMock(side_effect=Exception("Tile processing failed"))
    result, count = pts._fuse_level_tiles_parallel(0, 3, [1, 1, 1], 100, 100, 0)
    assert result.shape == (100, 100, 3)
    assert np.all(result == 0)


def test_temp_dir_manager_scenario():
    with patch('shinestacker.algorithms.base_stack_algo.AppConfig.get', return_value=''):
        pts = PyramidTilesStack()
        assert pts.temp_dir_manager is not None
        assert os.path.exists(pts.temp_dir_path)
        pts.print_message = MagicMock()
        temp_dir_path = pts.temp_dir_path
        pts.cleanup_temp_files()
        assert not os.path.exists(temp_dir_path)


def test_fuse_pyramids_no_tiled_layers():
    pts = PyramidTilesStack(n_tiled_layers=0)
    pts.print_message = MagicMock()
    pts.check_running = MagicMock()
    pts.after_step = MagicMock()
    pts.process = MagicMock()
    pts.process.callback.return_value = None
    pts.load_level = MagicMock(return_value=np.random.rand(50, 50, 3))
    pts.fuse_laplacian = MagicMock(return_value=np.random.rand(50, 50, 3))
    pts.get_fused_base = MagicMock(return_value=np.random.rand(50, 50, 3))
    pts.filenames = ['img1.jpg', 'img2.jpg']
    pts.level_shapes = {0: [(50, 50)], 1: [(50, 50)]}
    all_level_counts = [1, 1]
    with patch.object(pts, '_fuse_level_tiles_serial') as mock_serial, \
         patch.object(pts, '_fuse_level_tiles_parallel') as mock_parallel:
        result = pts.fuse_pyramids(all_level_counts)
        assert len(result) == 1
        mock_serial.assert_not_called()
        mock_parallel.assert_not_called()


def test_fuse_pyramids_empty_level():
    pts = PyramidTilesStack()
    pts.print_message = MagicMock()
    pts.check_running = MagicMock()
    pts.after_step = MagicMock()
    pts.process = MagicMock()
    pts.process.callback.return_value = None
    pts.filenames = ['img1.jpg', 'img2.jpg']
    pts.level_shapes = {0: [(50, 50)], 1: [(50, 50)]}
    all_level_counts = [1, 1]  # Both images only have level 0
    with patch.object(pts, '_fuse_level_tiles_serial') as mock_serial:
        pts.fuse_pyramids(all_level_counts)
        mock_serial.assert_not_called()


def test_safe_cleanup_with_retry():
    pts = PyramidTilesStack()
    pts.print_message = MagicMock()
    pts.cleanup_temp_files = MagicMock(side_effect=[Exception("First fail"), None])
    with patch('shinestacker.algorithms.pyramid_tiles.time.sleep') as mock_sleep:
        pts._safe_cleanup()
        assert pts.cleanup_temp_files.call_count == 2
        mock_sleep.assert_called_once_with(1)


def test_auto_fallback_keeps_output_filename(example_images):
    from shinestacker.config.constants import constants
    from shinestacker.algorithms.pyramid_auto import PyramidAutoStack
    from shinestacker.core.exceptions import RunStopException
    calls = []

    def callback(name, *args):
        if name in (constants.CALLBACKS_SET_TOTAL_ACTIONS,
                    constants.CALLBACK_UPDATE_FRAME_STATUS):
            calls.append((args[0], args[1]))
        return True

    process = MagicMock()
    process.callback = callback
    process.name = 'stack-action'
    process.output_path = 'stack-output'
    process.input_path = 'input'
    stack = PyramidAutoStack(mode='auto', memory_limit=0.1, max_threads=1)
    stack.set_process(process)
    stack.init(example_images)
    stack.set_output_filename('stack_0000_pyram.jpg')
    stack._implementation.focus_stack = MagicMock(side_effect=RunStopException('test'))
    stack.focus_stack()
    output_keys = {filename for module, filename in calls if module == 'stack-output'}
    assert output_keys == {'stack_0000_pyram.jpg'}
