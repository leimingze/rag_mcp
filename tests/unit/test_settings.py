"""Unit tests for Settings configuration loader."""

import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
import yaml

from src.core.settings import Settings, get_settings, reset_settings


@pytest.fixture
def sample_config() -> dict:
    """Sample configuration for testing."""
    return {
        "llm": {
            "provider": "azure",
            "model": "gpt-4o",
            "azure": {"endpoint": "https://test.openai.azure.com"},
        },
        "embedding": {
            "provider": "openai",
            "model": "text-embedding-3-small",
        },
        "vector_store": {"backend": "chroma", "chroma": {"path": "./data/db"}},
    }


@pytest.fixture
def temp_config_file(sample_config: dict, temp_dir: Path) -> Path:
    """Create a temporary configuration file."""
    config_path = temp_dir / "settings.yaml"
    with open(config_path, "w") as f:
        yaml.dump(sample_config, f)
    return config_path


class TestSettings:
    """Tests for Settings class."""

    def test_load_config(self, temp_config_file: Path):
        """Test loading configuration from file."""
        settings = Settings(config_path=temp_config_file)

        assert settings.llm.provider == "azure"
        assert settings.llm.model == "gpt-4o"
        assert settings.embedding.provider == "openai"

    def test_nested_access(self, temp_config_file: Path):
        """Test nested configuration access."""
        settings = Settings(config_path=temp_config_file)

        assert settings.llm.azure.endpoint == "https://test.openai.azure.com"
        assert settings.vector_store.chroma.path == "./data/db"

    def test_get_method(self, temp_config_file: Path):
        """Test get method with dot notation."""
        settings = Settings(config_path=temp_config_file)

        assert settings.get("llm.provider") == "azure"
        assert settings.get("llm.model") == "gpt-4o"
        assert settings.get("nonexistent.key", "default") == "default"

    def test_section_proxy_keys(self, temp_config_file: Path):
        """Test SectionProxy keys method."""
        settings = Settings(config_path=temp_config_file)

        assert "provider" in settings.llm.keys()
        assert "model" in settings.llm.keys()

    def test_section_proxy_contains(self, temp_config_file: Path):
        """Test 'in' operator on SectionProxy."""
        settings = Settings(config_path=temp_config_file)

        assert "provider" in settings.llm
        assert "nonexistent" not in settings.llm

    def test_env_var_substitution(self, temp_dir: Path):
        """Test environment variable substitution."""
        config = {
            "llm": {
                "api_key": "${TEST_API_KEY}",
                "endpoint": "${TEST_ENDPOINT:http://localhost}",
            }
        }
        config_path = temp_dir / "settings.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        with mock.patch.dict(os.environ, {"TEST_API_KEY": "test-key-123"}):
            settings = Settings(config_path=config_path)

            assert settings.llm.api_key == "test-key-123"
            assert settings.llm.endpoint == "http://localhost"

    def test_env_var_with_default(self, temp_dir: Path):
        """Test environment variable with default value."""
        config = {"endpoint": "${MISSING_VAR:default-value}"}
        config_path = temp_dir / "settings.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        settings = Settings(config_path=config_path)
        assert settings.get("endpoint") == "default-value"

    def test_reload(self, temp_config_file: Path):
        """Test reloading configuration."""
        settings = Settings(config_path=temp_config_file)
        assert settings.llm.provider == "azure"

        # Modify the config file
        with open(temp_config_file, "r") as f:
            config = yaml.safe_load(f)
        config["llm"]["provider"] = "openai"
        with open(temp_config_file, "w") as f:
            yaml.dump(config, f)

        settings.reload()
        assert settings.llm.provider == "openai"

    def test_missing_config_file(self, temp_dir: Path):
        """Test error when config file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            Settings(config_path=temp_dir / "nonexistent.yaml")

    def test_project_root_detection(self, temp_config_file: Path):
        """Test project root auto-detection."""
        settings = Settings(
            config_path=temp_config_file,
            project_root=temp_config_file.parent,
        )

        assert settings.project_root == temp_config_file.parent

    def test_empty_config(self, temp_dir: Path):
        """Test with empty configuration file."""
        config_path = temp_dir / "empty.yaml"
        config_path.write_text("")

        settings = Settings(config_path=config_path)

        # Should return empty SectionProxy for any section
        assert settings.llm.as_dict() == {}

    def test_config_property(self, temp_config_file: Path):
        """Test config property returns copy."""
        settings = Settings(config_path=temp_config_file)

        config1 = settings.config
        config2 = settings.config

        assert config1 is not config2  # Different objects
        assert config1 == config2  # Same content


class TestGlobalSettings:
    """Tests for global settings instance."""

    def test_get_settings_singleton(self, temp_config_file: Path):
        """Test get_settings returns singleton instance."""
        reset_settings()

        settings1 = get_settings(config_path=temp_config_file)
        settings2 = get_settings()

        assert settings1 is settings2

    def test_reset_settings(self, temp_config_file: Path):
        """Test reset_settings clears global instance."""
        reset_settings()
        settings1 = get_settings(config_path=temp_config_file)

        reset_settings()
        settings2 = get_settings(config_path=temp_config_file)

        assert settings1 is not settings2

    def test_reload_param(self, temp_config_file: Path):
        """Test reload parameter in get_settings."""
        reset_settings()
        settings = get_settings(config_path=temp_config_file)

        assert settings.llm.provider == "azure"

        # Modify and reload
        with open(temp_config_file, "r") as f:
            config = yaml.safe_load(f)
        config["llm"]["provider"] = "openai"
        with open(temp_config_file, "w") as f:
            yaml.dump(config, f)

        reloaded = get_settings(reload=True)
        assert reloaded.llm.provider == "openai"
