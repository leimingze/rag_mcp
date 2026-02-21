"""Tests for core.settings module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.settings import Settings, load_settings, reload_settings


class TestSettings:
    """Test Settings class."""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary configuration file."""
        config_data = {
            "llm": {
                "provider": "azure",
                "model": "gpt-4o",
                "temperature": 0.7,
            },
            "embedding": {
                "provider": "openai",
                "model": "text-embedding-3-small",
            },
            "vector_store": {
                "backend": "chroma",
                "chroma": {
                    "path": "./data/db/chroma",
                },
            },
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        yield temp_path

        # Cleanup
        os.unlink(temp_path)

    @pytest.fixture
    def settings(self, temp_config_file):
        """Create a Settings instance with temporary config."""
        return Settings(temp_config_file)

    def test_init_with_path(self, temp_config_file):
        """Test initialization with config path."""
        settings = Settings(temp_config_file)
        assert settings.config_path == Path(temp_config_file).resolve()
        assert settings.config is not None
        assert isinstance(settings.config, dict)

    def test_init_loads_config(self, settings):
        """Test that configuration is loaded correctly."""
        assert settings.config["llm"]["provider"] == "azure"
        assert settings.config["embedding"]["provider"] == "openai"
        assert settings.config["vector_store"]["backend"] == "chroma"

    def test_env_var_expansion(self):
        """Test environment variable expansion in config."""
        os.environ["TEST_VAR"] = "test_value"
        os.environ["TEST_VAR_WITH_DEFAULT"] = ""

        config_data = {
            "llm": {
                "provider": "azure",
                "api_key": "${TEST_VAR}",
                "endpoint": "${TEST_VAR_WITH_DEFAULT:-default_endpoint}",
            },
            "embedding": {
                "provider": "openai",
            },
            "vector_store": {
                "backend": "chroma",
            },
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            settings = Settings(temp_path)
            assert settings.config["llm"]["api_key"] == "test_value"
            assert settings.config["llm"]["endpoint"] == "default_endpoint"
        finally:
            os.unlink(temp_path)
            del os.environ["TEST_VAR"]
            del os.environ["TEST_VAR_WITH_DEFAULT"]

    def test_get_method(self, settings):
        """Test the get() method with dot notation."""
        assert settings.get("llm.provider") == "azure"
        assert settings.get("llm.model") == "gpt-4o"
        assert settings.get("llm.temperature") == 0.7
        assert settings.get("nonexistent.key", "default") == "default"
        assert settings.get("nonexistent") is None

    def test_get_section(self, settings):
        """Test getting entire configuration sections."""
        llm_config = settings.get_section("llm")
        assert isinstance(llm_config, dict)
        assert llm_config["provider"] == "azure"
        assert llm_config["model"] == "gpt-4o"

    def test_get_section_nonexistent(self, settings):
        """Test getting nonexistent section raises KeyError."""
        with pytest.raises(KeyError):
            settings.get_section("nonexistent")

    def test_property_accessors(self, settings):
        """Test property-based section accessors."""
        assert isinstance(settings.llm_config, dict)
        assert settings.llm_config["provider"] == "azure"

        assert isinstance(settings.embedding_config, dict)
        assert settings.embedding_config["provider"] == "openai"

        assert isinstance(settings.vector_store_config, dict)
        assert settings.vector_store_config["backend"] == "chroma"

    def test_missing_required_section(self):
        """Test validation error for missing required sections."""
        config_data = {
            "llm": {"provider": "azure"},
            # Missing embedding and vector_store
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Missing required configuration sections"):
                Settings(temp_path)
        finally:
            os.unlink(temp_path)

    def test_file_not_found(self):
        """Test FileNotFoundError for nonexistent config file."""
        with pytest.raises(FileNotFoundError):
            Settings("/nonexistent/path/settings.yaml")

    def test_repr(self, settings):
        """Test string representation."""
        repr_str = repr(settings)
        assert "Settings" in repr_str
        assert "config_path" in repr_str


class TestGlobalSettings:
    """Test global settings functions."""

    def test_load_settings_singleton(self):
        """Test that load_settings returns singleton instance."""
        # Reset global settings
        import core.settings
        core.settings._global_settings = None

        config_data = {
            "llm": {"provider": "azure"},
            "embedding": {"provider": "openai"},
            "vector_store": {"backend": "chroma"},
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            settings1 = load_settings(temp_path)
            settings2 = load_settings()

            assert settings1 is settings2
        finally:
            os.unlink(temp_path)
            core.settings._global_settings = None

    def test_reload_settings(self):
        """Test reload_settings forces reload."""
        import core.settings
        core.settings._global_settings = None

        config_data1 = {
            "llm": {"provider": "azure"},
            "embedding": {"provider": "openai"},
            "vector_store": {"backend": "chroma"},
        }
        config_data2 = {
            "llm": {"provider": "openai"},
            "embedding": {"provider": "openai"},
            "vector_store": {"backend": "chroma"},
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data1, f)
            temp_path1 = f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data2, f)
            temp_path2 = f.name

        try:
            settings1 = load_settings(temp_path1)
            settings2 = reload_settings(temp_path2)

            assert settings1 is not settings2
            assert settings1.get("llm.provider") == "azure"
            assert settings2.get("llm.provider") == "openai"
        finally:
            os.unlink(temp_path1)
            os.unlink(temp_path2)
            core.settings._global_settings = None
