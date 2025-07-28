import pytest
from shinestacker.config.config import _Config, config


class TestConfig:
    def setup_method(self, method):
        _Config._instance = None
        _Config._initialized = False

    def test_singleton_pattern(self):
        config1 = _Config()
        config2 = _Config()
        assert config1 is config2

    def test_default_values(self):
        test_config = _Config()
        assert test_config.DISABLE_TQDM is False
        assert test_config.COMBINED_APP is False
        assert test_config.DONT_USE_NATIVE_MENU is True

    def test_init_method_valid_keys(self):
        test_config = _Config()
        test_config.init(
            DISABLE_TQDM=True,
            COMBINED_APP=True,
            DONT_USE_NATIVE_MENU=False
        )
        assert test_config.DISABLE_TQDM is True
        assert test_config.COMBINED_APP is True
        assert test_config.DONT_USE_NATIVE_MENU is False

    def test_init_method_invalid_key(self):
        test_config = _Config()
        with pytest.raises(AttributeError) as excinfo:
            test_config.init(INVALID_KEY=True)
        assert "Invalid config key" in str(excinfo.value)

    def test_init_method_already_initialized(self):
        test_config = _Config()
        test_config.init(DISABLE_TQDM=True)
        with pytest.raises(RuntimeError) as excinfo:
            test_config.init(DISABLE_TQDM=False)
        assert "Config already initialized" in str(excinfo.value)

    def test_property_access(self):
        test_config = _Config()
        assert test_config.DISABLE_TQDM == test_config._DISABLE_TQDM
        assert test_config.COMBINED_APP == test_config._COMBINED_APP
        assert test_config.DONT_USE_NATIVE_MENU == test_config._DONT_USE_NATIVE_MENU

    def test_immutable_after_init(self):
        test_config = _Config()
        test_config.init(DISABLE_TQDM=True)
        with pytest.raises(AttributeError):
            test_config._DISABLE_TQDM = False
        test_config.some_new_attr = "value"

    def test_jupyter_notebook_detection(self):
        test_config = _Config()
        assert isinstance(test_config.JUPYTER_NOTEBOOK, bool)