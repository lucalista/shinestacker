# pylint: disable=C0114, C0115, C0116, C0103, W0201
from .. config.config import _ConfigBase


class _AppConfig(_ConfigBase):
    def __new__(cls):
        return _ConfigBase.__new__(cls)

    def _init_defaults(self):
        self._DONT_USE_NATIVE_MENU = True
        self._COMBINED_APP = False

    @property
    def DONT_USE_NATIVE_MENU(self):
        return self._DONT_USE_NATIVE_MENU

    @property
    def COMBINED_APP(self):
        return self._COMBINED_APP


app_config = _AppConfig()
