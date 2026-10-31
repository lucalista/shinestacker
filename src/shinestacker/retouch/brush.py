# pylint: disable=R0903
from .. config.app_config import AppConfig


class Brush:
    def __init__(self):
        self.size = AppConfig.get('brush_size')
        self.hardness = AppConfig.get('brush_hardness')
        self.opacity = AppConfig.get('brush_opacity')
        self.flow = AppConfig.get('brush_flow')
        self.luminosity = 0
