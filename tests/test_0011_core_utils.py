import unittest
from unittest.mock import patch
from shinestacker.algorithms.core_utils import check_path_exists, make_tqdm_bar


class TestCoreUtils(unittest.TestCase):

    @patch('os.path.exists')
    def test_check_path_exists_valid(self, mock_exists):
        mock_exists.return_value = True
        try:
            check_path_exists('/fake/valid/path')
        except Exception:
            self.fail("check_path_exists() raised unexpected exception.")

    @patch('os.path.exists')
    def test_check_path_exists_invalid(self, mock_exists):
        mock_exists.return_value = False
        with self.assertRaises(Exception) as context:
            check_path_exists('/fake/invalid/path')
        self.assertIn('Path does not exist', str(context.exception))

    @patch('shinestacker.algorithms.core_utils.config')
    def test_make_tqdm_bar_disabled(self, mock_config):
        mock_config.DISABLE_TQDM = True
        self.assertIsNone(make_tqdm_bar('Test', 100))

    @patch('shinestacker.algorithms.core_utils.tqdm')
    @patch('shinestacker.algorithms.core_utils.config')
    def test_make_tqdm_bar_terminal(self, mock_config, mock_tqdm):
        mock_config.DISABLE_TQDM = False
        mock_config.JUPYTER_NOTEBOOK = False
        make_tqdm_bar('Terminal', 100, ncols=120)
        mock_tqdm.assert_called_once_with(
            desc='Terminal',
            total=100,
            ncols=120
        )

    @patch('shinestacker.algorithms.core_utils.tqdm_notebook')
    @patch('shinestacker.algorithms.core_utils.config')
    def test_make_tqdm_bar_notebook(self, mock_config, mock_tqdm_notebook):
        mock_config.DISABLE_TQDM = False
        mock_config.JUPYTER_NOTEBOOK = True
        make_tqdm_bar('Notebook', 50)
        mock_tqdm_notebook.assert_called_once_with(
            desc='Notebook',
            total=50
        )


if __name__ == '__main__':
    unittest.main()
