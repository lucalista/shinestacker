from PySide6.QtWidgets import QFormLayout
from shinestacker.config.constants import constants
from shinestacker.gui.action_config import FIELD_COMBO
from shinestacker.gui.action_config_dialog import AlignFramesConfigurator
from shinestacker.gui.project_model import ActionConfig


def test_reset_restores_combo_defaults(qtbot):  # pylint: disable=unused-argument
    configurator = AlignFramesConfigurator(True, '.')
    configurator.create_form(QFormLayout(), ActionConfig(constants.ACTION_ALIGNFRAMES, {}))
    builder = configurator.get_builder()
    combos = {tag: field for tag, field in builder.fields.items() if field['type'] == FIELD_COMBO}
    for field in combos.values():
        field['widget'].setCurrentIndex(field['widget'].count() - 1)
    builder.reset_to_defaults()
    for tag, field in combos.items():
        default = field['default_value']
        values, options = field.get('values'), field.get('options')
        if values is not None:
            default = dict(zip(values, options)).get(default, default)
        assert default is not None, tag
        assert field['widget'].currentText() == str(default), tag
