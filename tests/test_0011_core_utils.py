import unittest
from unittest.mock import patch
from shinestacker.core.core_utils import get_app_base_path, check_path_exists, make_tqdm_bar


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

    @patch('shinestacker.core.core_utils.config')
    def test_make_tqdm_bar_disabled(self, mock_config):
        mock_config.DISABLE_TQDM = True
        self.assertIsNone(make_tqdm_bar('Test', 100))

    @patch('shinestacker.core.core_utils.tqdm')
    @patch('shinestacker.core.core_utils.config')
    def test_make_tqdm_bar_terminal(self, mock_config, mock_tqdm):
        mock_config.DISABLE_TQDM = False
        mock_config.JUPYTER_NOTEBOOK = False
        make_tqdm_bar('Terminal', 100, ncols=120)
        mock_tqdm.assert_called_once_with(
            desc='Terminal',
            total=100,
            ncols=120
        )

    @patch('shinestacker.core.core_utils.tqdm_notebook')
    @patch('shinestacker.core.core_utils.config')
    def test_make_tqdm_bar_notebook(self, mock_config, mock_tqdm_notebook):
        mock_config.DISABLE_TQDM = False
        mock_config.JUPYTER_NOTEBOOK = True
        make_tqdm_bar('Notebook', 50)
        mock_tqdm_notebook.assert_called_once_with(
            desc='Notebook',
            total=50
        )

    @patch('platform.system')
    @patch('os.path.realpath')
    @patch('os.path.dirname')
    @patch('os.path.abspath')
    @patch('os.path.dirname')
    @patch('sys.executable')
    @patch('sys.frozen', True, create=True)  # create=True allows mocking non-existent attribute
    def test_get_app_base_path_frozen_windows(self, mock_executable, mock_dirname1, mock_abspath,
                                              mock_dirname2, mock_realpath, mock_system):
        mock_system.return_value = 'Windows'
        mock_executable.return_value = 'C:\\Program Files\\shinestacker\\app.exe'
        mock_realpath.return_value = 'C:\\Program Files\\shinestacker\\app.exe'
        mock_dirname1.return_value = 'C:\\Program Files\\shinestacker'
        mock_dirname2.return_value = 'C:\\Program Files\\shinestacker'
        result = get_app_base_path()
        self.assertEqual(result, 'C:\\Program Files\\shinestacker')

    @patch('platform.system')
    @patch('os.path.realpath')
    @patch('os.path.dirname')
    @patch('sys.executable')
    @patch('sys.frozen', True, create=True)
    def test_get_app_base_path_frozen_windows_deep(self, mock_executable, mock_dirname,
                                                   mock_realpath, mock_system):
        mock_system.return_value = 'Windows'
        mock_executable.return_value = 'C:\\deep\\path\\to\\shinestacker\\bin\\app.exe'
        mock_realpath.return_value = 'C:\\deep\\path\\to\\shinestacker\\bin\\app.exe'
        mock_dirname.side_effect = [
            'C:\\deep\\path\\to\\shinestacker\\bin',
            'C:\\deep\\path\\to\\shinestacker'
        ]
        result = get_app_base_path()
        self.assertEqual(result, 'C:\\deep\\path\\to\\shinestacker')

    @patch('platform.system')
    @patch('os.path.realpath')
    @patch('os.path.dirname')
    @patch('sys.executable')
    @patch('sys.frozen', True, create=True)
    def test_get_app_base_path_frozen_linux(self, mock_executable, mock_dirname,
                                            mock_realpath, mock_system):
        mock_system.return_value = 'Linux'
        mock_executable.return_value = '/usr/local/shinestacker/bin/app'
        mock_realpath.return_value = '/usr/local/shinestacker/bin/app'
        mock_dirname.side_effect = [
            '/usr/local/shinestacker/bin',
            '/usr/local/shinestacker'
        ]
        result = get_app_base_path()
        self.assertEqual(result, '/usr/local/shinestacker')


if __name__ == '__main__':
    unittest.main()
