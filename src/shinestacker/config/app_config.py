from .settings import Settings


class AppConfig:
    _instance = None

    def __init__(self):
        if AppConfig._instance is not None:
            raise RuntimeError("AppConfig is a singleton.")
        self.config = {}
        Settings.add_observer(self)
        self.update(Settings.instance().settings)

    def update(self, settings):
        self.config = {**self.config, **settings}

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def get(cls, key, default=None):
        return cls.instance().config.get(key, default)

    @classmethod
    def set(cls, key, value):
        cls.instance().config[key] = value
