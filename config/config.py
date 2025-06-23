class _Config:
    _initialized = False
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_defaults()
        return cls._instance

    def _init_defaults(self):
        self._DISABLE_TQDM = False
        self._TRAP_RUN_EXCEPTIONS = True
        try:
            __IPYTHON__ # noqa
            self._JUPYTER_NOTEBOOK = True
        except Exception:
            self._JUPYTER_NOTEBOOK = False

    def init(self, **kwargs):
        if self._initialized:
            raise RuntimeError("Config already initialized")
        for k, v in kwargs.items():
            if hasattr(self, f"_{k}"):
                setattr(self, f"_{k}", v)
            else:
                raise AttributeError(f"Invalid config key: {k}")
        self._initialized = True

    @property
    def DISABLE_TQDM(self):
        return self._DISABLE_TQDM

    @property
    def TRAP_RUN_EXCEPTIONS(self):
        return self._TRAP_RUN_EXCEPTIONS

    @property
    def JUPYTER_NOTEBOOK(self):
        return self._JUPYTER_NOTEBOOK

    def __setattr__(self, name, value):
        if self._initialized and name.startswith('_'):
            raise AttributeError("Can't change config after initialization")
        super().__setattr__(name, value)


config = _Config()
