import unittest
from unittest.mock import Mock, patch
import numpy as np
from shinestacker.algorithms.align_auto import AlignFramesAuto
from shinestacker.config.constants import constants
from shinestacker.config.defaults import DEFAULTS


class TestAlignFramesAuto(unittest.TestCase):
    @patch('shinestacker.algorithms.align_auto.os.cpu_count')
    def test_init_default_values(self, mock_cpu_count):
        mock_cpu_count.return_value = 8
        align_auto = AlignFramesAuto()
        self.assertEqual(align_auto.mode, DEFAULTS['align_frames_params']['align_mode'])
        self.assertEqual(align_auto.memory_limit, DEFAULTS['align_frames_params']['memory_limit'])
        self.assertEqual(align_auto.max_threads, DEFAULTS['align_frames_params']['max_threads'])
        self.assertEqual(align_auto.chunk_submit, DEFAULTS['align_frames_params']['chunk_submit'])
        self.assertEqual(align_auto.bw_matching, DEFAULTS['align_frames_params']['bw_matching'])
        self.assertEqual(align_auto.num_threads,
                         min(DEFAULTS['align_frames_params']['max_threads'], 8))
        self.assertIsNone(align_auto._implementation)

    @patch('shinestacker.algorithms.align_auto.os.cpu_count')
    def test_init_custom_values(self, mock_cpu_count):
        mock_cpu_count.return_value = 8
        align_auto = AlignFramesAuto(
            mode='parallel',
            memory_limit=8,
            max_threads=16,
            chunk_submit=True,
            bw_matching=True,
            custom_arg='test'
        )
        self.assertEqual(align_auto.mode, 'parallel')
        self.assertEqual(align_auto.memory_limit, 8)
        self.assertEqual(align_auto.max_threads, 16)
        self.assertEqual(align_auto.chunk_submit, True)
        self.assertEqual(align_auto.bw_matching, True)
        self.assertEqual(align_auto.num_threads, 8)
        self.assertEqual(align_auto.kwargs['custom_arg'], 'test')

    @patch('shinestacker.algorithms.align_auto.os.cpu_count')
    def test_init_limited_cores(self, mock_cpu_count):
        mock_cpu_count.return_value = 2
        align_auto = AlignFramesAuto(max_threads=4)
        self.assertEqual(align_auto.num_threads, 2)

    @patch('shinestacker.algorithms.align_auto.AlignFrames')
    @patch('shinestacker.algorithms.align_auto.os.cpu_count')
    def test_begin_sequential_mode(self, mock_cpu_count, mock_align_frames):
        mock_cpu_count.return_value = 8
        mock_process = Mock()
        align_auto = AlignFramesAuto(mode='sequential')
        align_auto.begin(mock_process)
        mock_align_frames.assert_called_once()
        mock_align_frames.return_value.begin.assert_called_once_with(mock_process)

    @patch('shinestacker.algorithms.align_auto.AlignFrames')
    @patch('shinestacker.algorithms.align_auto.os.cpu_count')
    def test_begin_single_thread(self, mock_cpu_count, mock_align_frames):
        mock_cpu_count.return_value = 1
        mock_process = Mock()
        align_auto = AlignFramesAuto()
        align_auto.begin(mock_process)
        mock_align_frames.assert_called_once()
        mock_align_frames.return_value.begin.assert_called_once_with(mock_process)

    @patch('shinestacker.algorithms.align_auto.AlignFramesParallel')
    @patch('shinestacker.algorithms.align_auto.os.cpu_count')
    def test_begin_parallel_mode(self, mock_cpu_count, mock_align_parallel):
        mock_cpu_count.return_value = 8
        mock_process = Mock()
        align_auto = AlignFramesAuto(mode='parallel')
        align_auto.begin(mock_process)
        mock_align_parallel.assert_called_once()
        mock_align_parallel.return_value.begin.assert_called_once_with(mock_process)

    @patch('shinestacker.algorithms.align_auto.get_first_image_file')
    @patch('shinestacker.algorithms.align_auto.read_img')
    @patch('shinestacker.algorithms.align_auto.AlignFramesParallel')
    @patch('shinestacker.algorithms.align_auto.os.cpu_count')
    def test_begin_auto_mode_memory_intensive(
            self, mock_cpu_count, mock_align_parallel,
            mock_read_img,
            mock_get_first_image):
        mock_cpu_count.return_value = 8
        mock_process = Mock()
        mock_process.input_filepaths.return_value = ['test.jpg']
        mock_get_first_image.return_value = 'test.jpg'
        mock_img = np.ones((1000, 1000, 3), dtype=np.uint8)
        mock_read_img.return_value = mock_img
        align_auto = AlignFramesAuto(
            mode='auto',
            feature_config={
                'detector': constants.DETECTOR_SIFT,
                'descriptor': constants.DESCRIPTOR_SIFT
            }
        )
        align_auto.begin(mock_process)
        mock_align_parallel.assert_called_once()
        mock_align_parallel.return_value.begin.assert_called_once_with(mock_process)

    @patch('shinestacker.algorithms.align_auto.AlignFramesParallel')
    @patch('shinestacker.algorithms.align_auto.os.cpu_count')
    def test_begin_auto_mode_non_memory_intensive(
            self, mock_cpu_count, mock_align_parallel):
        mock_cpu_count.return_value = 8
        mock_process = Mock()
        align_auto = AlignFramesAuto(
            mode='auto',
            feature_config={
                'detector': DEFAULTS['align_frames_params']['detector'],
                'descriptor': DEFAULTS['align_frames_params']['descriptor']
            }
        )
        align_auto.begin(mock_process)
        mock_align_parallel.assert_called_once()
        mock_align_parallel.return_value.begin.assert_called_once_with(mock_process)

    @patch('shinestacker.algorithms.align_auto.AlignFrames')
    @patch('shinestacker.algorithms.align_auto.os.cpu_count')
    def test_delegate_methods(self, mock_cpu_count, mock_align_frames):
        mock_cpu_count.return_value = 1
        mock_process = Mock()
        align_auto = AlignFramesAuto()
        align_auto.begin(mock_process)
        align_auto.align_images(1, 'img_ref', 'img_0')
        mock_align_frames.return_value.align_images.assert_called_once_with(1, 'img_ref', 'img_0')
        align_auto.run_frame(1, 0, 'img_0')
        mock_align_frames.return_value.run_frame.assert_called_once_with(1, 0, 'img_0')
        align_auto.sequential_processing()
        mock_align_frames.return_value.sequential_processing.assert_called_once()
        align_auto.end()
        mock_align_frames.return_value.end.assert_called_once()

    @patch('shinestacker.algorithms.align_auto.get_first_image_file')
    @patch('shinestacker.algorithms.align_auto.read_img')
    @patch('shinestacker.algorithms.align_auto.AlignFramesParallel')
    @patch('shinestacker.algorithms.align_auto.os.cpu_count')
    def test_begin_auto_mode_memory_intensive_akaze(
            self, mock_cpu_count, mock_align_parallel,
            mock_read_img,
            mock_get_first_image):
        mock_cpu_count.return_value = 8
        mock_process = Mock()
        mock_process.input_filepaths.return_value = ['test.jpg']
        mock_get_first_image.return_value = 'test.jpg'
        mock_img = np.ones((1000, 1000, 3), dtype=np.uint8)
        mock_read_img.return_value = mock_img
        align_auto = AlignFramesAuto(
            mode='auto',
            feature_config={
                'detector': constants.DETECTOR_AKAZE,
                'descriptor': constants.DESCRIPTOR_AKAZE
            }
        )
        align_auto.begin(mock_process)
        mock_align_parallel.assert_called_once()
        mock_align_parallel.return_value.begin.assert_called_once_with(mock_process)

    @patch('shinestacker.algorithms.align_auto.get_first_image_file')
    @patch('shinestacker.algorithms.align_auto.read_img')
    @patch('shinestacker.algorithms.align_auto.AlignFramesParallel')
    @patch('shinestacker.algorithms.align_auto.os.cpu_count')
    def test_begin_auto_mode_memory_calculation(
            self, mock_cpu_count, mock_align_parallel,
            mock_read_img,
            mock_get_first_image):
        mock_cpu_count.return_value = 8
        mock_process = Mock()
        mock_process.input_filepaths.return_value = ['test.jpg']
        mock_get_first_image.return_value = 'test.jpg'
        mock_img = np.ones((2000, 2000, 3), dtype=np.uint16)
        mock_read_img.return_value = mock_img
        align_auto = AlignFramesAuto(
            mode='auto',
            memory_limit=1,
            feature_config={
                'detector': constants.DETECTOR_SIFT,
                'descriptor': constants.DESCRIPTOR_SIFT
            }
        )
        align_auto.begin(mock_process)
        mock_align_parallel.assert_called_once()
        mock_align_parallel.return_value.begin.assert_called_once_with(mock_process)

    @patch('shinestacker.algorithms.align_auto.AlignFramesParallel')
    @patch('shinestacker.algorithms.align_auto.os.cpu_count')
    def test_begin_auto_mode_no_feature_config(self, mock_cpu_count, mock_align_parallel):
        mock_cpu_count.return_value = 8
        mock_process = Mock()
        align_auto = AlignFramesAuto(mode='auto')
        align_auto.begin(mock_process)
        mock_align_parallel.assert_called_once()
        mock_align_parallel.return_value.begin.assert_called_once_with(mock_process)

    @patch('shinestacker.algorithms.align_auto.AlignFramesParallel')
    @patch('shinestacker.algorithms.align_auto.os.cpu_count')
    def test_begin_auto_mode_with_kwargs(self, mock_cpu_count, mock_align_parallel):
        mock_cpu_count.return_value = 8
        mock_process = Mock()
        align_auto = AlignFramesAuto(
            mode='auto',
            feature_config={'detector': 'ORB'},
            matching_config={'method': 'FLANN'},
            alignment_config={'method': 'homography'},
            custom_setting='test_value'
        )
        align_auto.begin(mock_process)
        mock_align_parallel.assert_called_once()
        mock_align_parallel.return_value.begin.assert_called_once_with(mock_process)

    @patch('shinestacker.algorithms.align_auto.AlignFramesParallel')
    @patch('shinestacker.algorithms.align_auto.os.cpu_count')
    def test_begin_parallel_mode_with_chunk_submit(self, mock_cpu_count, mock_align_parallel):
        mock_cpu_count.return_value = 8
        mock_process = Mock()
        align_auto = AlignFramesAuto(mode='parallel', chunk_submit=True)
        align_auto.begin(mock_process)
        mock_align_parallel.assert_called_once()
        mock_align_parallel.return_value.begin.assert_called_once_with(mock_process)

    @patch('shinestacker.algorithms.align_auto.AlignFramesParallel')
    @patch('shinestacker.algorithms.align_auto.os.cpu_count')
    def test_begin_parallel_mode_with_bw_matching(self, mock_cpu_count, mock_align_parallel):
        mock_cpu_count.return_value = 8
        mock_process = Mock()
        align_auto = AlignFramesAuto(mode='parallel', bw_matching=True)
        align_auto.begin(mock_process)
        mock_align_parallel.assert_called_once()
        mock_align_parallel.return_value.begin.assert_called_once_with(mock_process)

    @patch('shinestacker.algorithms.align_auto.AlignFramesParallel')
    @patch('shinestacker.algorithms.align_auto.os.cpu_count')
    def test_begin_auto_mode_memory_limit_zero_threads(self, mock_cpu_count, mock_align_parallel):
        mock_cpu_count.return_value = 8
        mock_process = Mock()
        align_auto = AlignFramesAuto(mode='auto', memory_limit=0.001)
        align_auto.begin(mock_process)
        mock_align_parallel.assert_called_once()
        mock_align_parallel.return_value.begin.assert_called_once_with(mock_process)

    @patch('shinestacker.algorithms.align_auto.AlignFrames')
    @patch('shinestacker.algorithms.align_auto.os.cpu_count')
    def test_sequential_processing_delegation(self, mock_cpu_count, mock_align_frames):
        mock_cpu_count.return_value = 1
        mock_process = Mock()
        align_auto = AlignFramesAuto()
        align_auto.begin(mock_process)
        align_auto.sequential_processing()
        mock_align_frames.return_value.sequential_processing.assert_called_once()

    @patch('shinestacker.algorithms.align_auto.AlignFramesParallel')
    @patch('shinestacker.algorithms.align_auto.os.cpu_count')
    def test_parallel_implementation_delegation(self, mock_cpu_count, mock_align_parallel):
        mock_cpu_count.return_value = 8
        mock_process = Mock()
        align_auto = AlignFramesAuto(mode='parallel')
        align_auto.begin(mock_process)
        align_auto.align_images(1, 'img_ref', 'img_0')
        mock_align_parallel.return_value.align_images.assert_called_once_with(1, 'img_ref', 'img_0')
        align_auto.run_frame(1, 0, 'img_0')
        mock_align_parallel.return_value.run_frame.assert_called_once_with(1, 0, 'img_0')
        align_auto.sequential_processing()
        mock_align_parallel.return_value.sequential_processing.assert_called_once()
        align_auto.end()
        mock_align_parallel.return_value.end.assert_called_once()


if __name__ == '__main__':
    unittest.main()


class TestAlignFramesAutoSiftThreads(unittest.TestCase):
    """SIFT used to be estimated at 0.1 GB per megapixel and byte (6.6 GB for a
    33 MP 16-bit frame), which forced one thread with the default memory limit."""

    def _threads(self, memory_limit, shape=(4680, 7020, 3)):
        with patch('shinestacker.algorithms.align_auto.os.cpu_count', return_value=16), \
                patch('shinestacker.algorithms.align_auto.get_first_image_file',
                      return_value='a.tif'), \
                patch('shinestacker.algorithms.align_auto.read_img',
                      return_value=np.zeros(shape, dtype=np.uint16)), \
                patch('shinestacker.algorithms.align_auto.AlignFramesParallel') as parallel, \
                patch('shinestacker.algorithms.align_auto.AlignFrames') as sequential:
            process = Mock()
            process.input_filepaths.return_value = ['a.tif']
            align_auto = AlignFramesAuto(mode='auto', memory_limit=memory_limit, max_threads=16,
                                         detector=constants.DETECTOR_SIFT,
                                         descriptor=constants.DESCRIPTOR_SIFT,
                                         match_method=constants.MATCHING_KNN)
            align_auto.begin(process)
            if sequential.called:
                return 1
            return parallel.call_args.kwargs['max_threads']

    def test_sift_33mp_runs_in_parallel(self):
        self.assertEqual(self._threads(8), 16)

    def test_sift_threads_bounded_by_memory(self):
        self.assertEqual(self._threads(0.5), 2)        # 0.197 GB per frame
        self.assertEqual(self._threads(0.1), 1)
