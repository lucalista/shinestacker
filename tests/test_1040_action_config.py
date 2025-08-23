import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication, QFormLayout
from shinestacker.gui.action_config_dialog import (
    FieldBuilder, ActionConfigDialog, DefaultActionConfigurator,
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


def test_action_config_dialog(qtbot, mock_action):
    mock_parent = MagicMock()
    mock_parent.expert_options = False
    mock_action.type_name = "ProjectEditor"
    with patch.object(ActionConfigDialog, 'parent', return_value=mock_parent):
        current_wd = '.'
        dialog = ActionConfigDialog(mock_action, current_wd)
        qtbot.addWidget(dialog)
    assert dialog.windowTitle() == f"Configure {mock_action.type_name}"
    assert dialog.layout is not None
    assert isinstance(dialog.configurator, DefaultActionConfigurator)
    assert dialog.layout.count() > 0


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
