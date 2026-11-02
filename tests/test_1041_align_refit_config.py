from PySide6.QtWidgets import QFormLayout
from shinestacker.config.constants import constants
from shinestacker.gui.action_config_dialog import AlignFramesConfigurator
from shinestacker.gui.project_model import ActionConfig


def test_align_refit_reset_to_default(qtbot):  # pylint: disable=unused-argument
    action = ActionConfig(constants.ACTION_ALIGNFRAMES, {})
    configurator = AlignFramesConfigurator(True, '.')
    configurator.create_form(QFormLayout(), action)
    builder = configurator.get_builder()
    refit = builder.fields['refit']['widget']
    refit.setCurrentText(AlignFramesConfigurator.REFIT_OPTIONS[1])
    builder.reset_to_defaults()
    assert refit.currentText() == AlignFramesConfigurator.REFIT_OPTIONS[0]
    params = {}
    builder.update_params(params)
    assert params['refit'] == constants.REFIT_NONE
