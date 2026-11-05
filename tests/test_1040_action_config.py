import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication, QFormLayout
from shinestacker.gui.action_config import FieldBuilder
from shinestacker.gui.action_config_dialog import (
    ActionConfigDialog, DefaultActionConfigurator,
    FIELD_TEXT, FIELD_ABS_PATH, FIELD_REL_PATH, FIELD_FLOAT,
    FIELD_INT, FIELD_INT_TUPLE, FIELD_BOOL, FIELD_COMBO)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.quit()


@pytest.fixture
def form_layout(qapp):
    layout = QFormLayout()
    yield layout
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget:
            widget.deleteLater()


@pytest.fixture
def mock_action():
    action = MagicMock()
    action.params = {}
    action.parent = None
    action.type_name = "TestAction"
    return action


def test_field_builder_add_field(form_layout, mock_action, qapp):
    current_wd = '.'
    builder = FieldBuilder(form_layout, mock_action, current_wd)
    text_field = builder.add_field('text_field', FIELD_TEXT, 'Test Text Field')
    assert text_field is not None
    assert 'text_field' in builder.fields
    abs_path_field = builder.add_field('abs_path', FIELD_ABS_PATH, 'Absolute Path')
    assert abs_path_field is not None
    assert 'abs_path' in builder.fields
    rel_path_field = builder.add_field('rel_path', FIELD_REL_PATH, 'Relative Path')
    assert rel_path_field is not None
    assert 'rel_path' in builder.fields
    float_field = builder.add_field('float_field', FIELD_FLOAT, 'Float Field', default=3.14)
    assert float_field is not None
    assert 'float_field' in builder.fields
    int_field = builder.add_field('int_field', FIELD_INT, 'Integer Field')
    assert int_field is not None
    assert 'int_field' in builder.fields
    int_tuple_field = builder.add_field('int_tuple', FIELD_INT_TUPLE, 'Integer Tuple',
                                        size=2, labels=('X', 'Y'))
    assert int_tuple_field is not None
    assert 'int_tuple' in builder.fields
    bool_field = builder.add_field('bool_field', FIELD_BOOL, 'Boolean Field')
    assert bool_field is not None
    assert 'bool_field' in builder.fields
    combo_field = builder.add_field('combo_field', FIELD_COMBO, 'Combo Field',
                                    options=['Option1', 'Option2'])
    assert combo_field is not None
    assert 'combo_field' in builder.fields


def test_action_config_dialog(qtbot, mock_action, mocker):
    mock_action.type_name = "ProjectEditor"
    current_wd = '.'
    mocker.patch('shinestacker.gui.config_dialog.ConfigDialog.adjust_dialog_size')
    dialog = ActionConfigDialog(mock_action, current_wd)
    qtbot.addWidget(dialog)
    assert dialog.windowTitle() == f"Configure {mock_action.type_name}"
    assert dialog.form_layout is not None
    assert isinstance(dialog.configurator, DefaultActionConfigurator)


def test_field_builder_update_params(form_layout, mock_action, tmp_path, qapp):
    current_wd = '.'
    builder = FieldBuilder(form_layout, mock_action, current_wd)
    builder.add_field('text_field', FIELD_TEXT, 'Text Field')
    builder.add_field('abs_path', FIELD_ABS_PATH, 'Absolute Path')
    builder.add_field(
        'float_field', FIELD_FLOAT,
        'Float Field', default=3.14, min_val=0.0, max_val=10.0, step=0.1)
    builder.add_field('int_field', FIELD_INT, 'Integer Field')
    builder.add_field('bool_field', FIELD_BOOL, 'Boolean Field')
    builder.add_field('combo_field', FIELD_COMBO, 'Combo Field',
                      options=['Option1', 'Option2'], default='Option1')
    builder.fields['text_field']['widget'].setText("Test Value")
    builder.fields['abs_path']['widget'].layout().itemAt(0).widget().setText(str(tmp_path))
    builder.fields['float_field']['widget'].setValue(3.14)
    builder.fields['int_field']['widget'].setValue(42)
    builder.fields['bool_field']['widget'].setChecked(True)
    builder.fields['combo_field']['widget'].setCurrentText("Option1")
    params = {}
    with patch('PySide6.QtWidgets.QMessageBox.warning') as mock_warning:
        result = builder.update_params(params)
    assert result is True
    assert params['text_field'] == "Test Value"
    assert params['abs_path'] == str(tmp_path)
    assert params['float_field'] == pytest.approx(3.14)
    assert params['int_field'] == 42
    assert params['bool_field'] is True
    assert params['combo_field'] == "Option1"
    mock_warning.assert_not_called()


def test_field_builder_required_fields(form_layout, mock_action, qapp):
    current_wd = '.'
    builder = FieldBuilder(form_layout, mock_action, current_wd)
    builder.add_field('required_field', FIELD_TEXT, 'Required Field', required=True)
    builder.fields['required_field']['widget'].setText("")
    params = {}
    with patch('PySide6.QtWidgets.QMessageBox.warning') as mock_warning:
        result = builder.update_params(params)
        if not result:
            params.clear()
    assert result is False
    assert params == {}
    mock_warning.assert_called_once()


SIFT_DEFAULTS = {'detector': 'SIFT', 'descriptor': 'SIFT', 'match_method': 'KNN',
                 'sift_backend': 'opencv'}


def _default_params(**overrides):
    # AppConfig reads the user's settings file, and the built-in detector is ORB, so the
    # dialog gets fixed defaults: the built-in ones with a SIFT setup, unless overridden
    from shinestacker.config.app_config import AppConfig
    from shinestacker.config.defaults import DEFAULTS
    get = AppConfig.get
    defaults = {**DEFAULTS['align_frames_params'], **SIFT_DEFAULTS, **overrides}
    return patch.object(AppConfig, 'get', side_effect=lambda key, default=None: (
        defaults if key == 'align_frames_params' else get(key, default)))


def _align_dialog(mock_action, params, silx=True, **defaults):
    # silx: whether the opencl extra (silx, pyopencl) is installed
    mock_action.type_name = "AlignFrames"
    mock_action.params = {'border_value': [0, 0, 0, 0], **params}
    with patch('shinestacker.gui.config_dialog.ConfigDialog.adjust_dialog_size'), \
            patch('shinestacker.gui.action_config_dialog.silx_installed', return_value=silx), \
            _default_params(**defaults):
        return ActionConfigDialog(mock_action, '.')


def _labels(menu):
    return [menu.itemText(i) for i in range(menu.count())]


def _collect(dialog):
    params = {}
    with patch('PySide6.QtWidgets.QMessageBox.warning'):
        assert dialog.configurator.update_params(params)
    return params


def test_align_detector_menu_sets_sift_backend(mock_action, qapp):
    dialog = _align_dialog(mock_action, {})
    menu = dialog.configurator.detector_field
    labels = _labels(menu)
    assert labels[:2] == ['SIFT (OpenCV)', 'SIFT (silx)']
    assert 'ORB' in labels
    params = _collect(dialog)
    assert (params['detector'], params['sift_backend']) == ('SIFT', 'opencv')
    for label, backend in (('SIFT (silx)', 'silx'), ('ORB', 'opencv')):
        menu.setCurrentText(label)
        params = _collect(dialog)
        assert params['detector'] == label.split(' ')[0]
        assert params['sift_backend'] == backend


def test_align_detector_menu_from_params(mock_action, qapp):
    dialog = _align_dialog(mock_action, {'detector': 'SIFT', 'sift_backend': 'silx'})
    assert dialog.configurator.detector_field.currentText() == 'SIFT (silx)'
    dialog = _align_dialog(mock_action, {'detector': 'ORB', 'sift_backend': 'opencv'})
    assert dialog.configurator.detector_field.currentText() == 'ORB'


def test_align_detector_menu_validates_sift_entries(mock_action, qapp):
    dialog = _align_dialog(mock_action, {'detector': 'SIFT', 'sift_backend': 'silx'})
    descriptor = dialog.configurator.descriptor_field
    descriptor.blockSignals(True)
    descriptor.setCurrentText('ORB')
    descriptor.blockSignals(False)
    with patch('shinestacker.gui.action_config_dialog.QMessageBox.warning') as warning:
        assert not dialog.configurator.update_params({})
    warning.assert_called_once()


def test_align_detector_menu_sift_default_is_opencv(mock_action, qapp):
    dialog = _align_dialog(mock_action, {})
    menu = dialog.configurator.detector_field
    assert menu.currentText() == 'SIFT (OpenCV)'
    menu.setCurrentText('SIFT (silx)')
    dialog.configurator.builder.reset_to_defaults()
    assert menu.currentText() == 'SIFT (OpenCV)'


def test_align_detector_menu_silx_default(mock_action, qapp):
    dialog = _align_dialog(mock_action, {}, detector='SIFT', sift_backend='silx')
    menu = dialog.configurator.detector_field
    assert menu.currentText() == 'SIFT (silx)'
    menu.setCurrentText('ORB')
    dialog.configurator.builder.reset_to_defaults()
    assert menu.currentText() == 'SIFT (silx)'


def test_align_detector_menu_old_project_is_opencv(mock_action, qapp):
    dialog = _align_dialog(mock_action, {'detector': 'SIFT'})
    assert dialog.configurator.detector_field.currentText() == 'SIFT (OpenCV)'
    assert _collect(dialog)['sift_backend'] == 'opencv'


def test_align_detector_menu_without_opencl_extra(mock_action, qapp):
    dialog = _align_dialog(mock_action, {}, silx=False)
    menu = dialog.configurator.detector_field
    assert 'SIFT (silx)' not in _labels(menu)
    assert 'silx' not in menu.toolTip()
    assert menu.currentText() == 'SIFT (OpenCV)'
    assert _collect(dialog)['sift_backend'] == 'opencv'


def test_align_detector_menu_without_opencl_extra_silx_default(mock_action, qapp):
    # a silx default from the settings of an installation with the extra
    dialog = _align_dialog(mock_action, {}, silx=False, detector='SIFT', sift_backend='silx')
    menu = dialog.configurator.detector_field
    assert 'SIFT (silx)' not in _labels(menu)
    assert menu.currentText() == 'SIFT (OpenCV)'
    menu.setCurrentText('ORB')
    dialog.configurator.builder.reset_to_defaults()
    assert menu.currentText() == 'SIFT (OpenCV)'


def test_align_detector_menu_without_opencl_extra_keeps_project_setting(mock_action, qapp):
    # a project made with the extra keeps its setting; alignment falls back to OpenCV
    dialog = _align_dialog(mock_action, {'detector': 'SIFT', 'sift_backend': 'silx'}, silx=False)
    menu = dialog.configurator.detector_field
    assert menu.currentText() == 'SIFT (silx)'
    assert _collect(dialog)['sift_backend'] == 'silx'
