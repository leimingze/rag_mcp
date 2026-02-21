"""Core settings module.

This module provides configuration loading functionality for the RAG MCP framework.
It handles loading and validating YAML configuration files with environment variable
expansion support.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class Settings:
    """Configuration settings loader and validator.

    This class handles loading configuration from YAML files, expanding
    environment variables, and validating the configuration structure.

    Attributes:
        config: The loaded configuration dictionary.
        config_path: Path to the configuration file.
    """

    # Default configuration paths to search
    DEFAULT_CONFIG_PATHS = [
        "config/settings.yaml",
        "config/settings.yml",
        "./settings.yaml",
        "./settings.yml",
    ]

    # Required top-level sections
    REQUIRED_SECTIONS = [
        "llm",
        "embedding",
        "vector_store",
    ]

    def __init__(self, config_path: Optional[str] = None):
        """Initialize Settings.

        Args:
            config_path: Path to the configuration file. If None, searches
                in default locations.

        Raises:
            FileNotFoundError: If no configuration file is found.
            ValueError: If the configuration is invalid.
        """
        self.config_path: Optional[Path] = None
        self.config: Dict[str, Any] = {}

        if config_path:
            self.config_path = Path(config_path).resolve()
            self._load()
        else:
            self._find_and_load_config()

        self._validate_config()

    def _find_and_load_config(self) -> None:
        """Search for configuration file in default locations.

        Raises:
            FileNotFoundError: If no configuration file is found.
        """
        for path_str in self.DEFAULT_CONFIG_PATHS:
            path = Path(path_str)
            if path.exists():
                self.config_path = path.resolve()
                self._load()
                return

        raise FileNotFoundError(
            f"Configuration file not found. Searched in: {self.DEFAULT_CONFIG_PATHS}"
        )

    def _load(self) -> None:
        """Load configuration from YAML file.

        Raises:
            FileNotFoundError: If the configuration file doesn't exist.
            ValueError: If the YAML is invalid.
        """
        if not self.config_path or not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                raw_config = yaml.safe_load(f)

            if raw_config is None:
                raise ValueError("Configuration file is empty")

            # Expand environment variables
            self.config = self._expand_env_vars(raw_config)

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")

    def _expand_env_vars(self, config: Any) -> Any:
        """Recursively expand environment variables in configuration.

        Supports the following syntax:
        - ${VAR_NAME} - Use environment variable, empty string if not set
        - ${VAR_NAME:-default} - Use environment variable if non-empty,
          otherwise use default value

        Args:
            config: Configuration value (dict, list, or string).

        Returns:
            Configuration with environment variables expanded.
        """
        if isinstance(config, dict):
            return {k: self._expand_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._expand_env_vars(item) for item in config]
        elif isinstance(config, str):
            # Match ${VAR} or ${VAR:-default}
            pattern = re.compile(r'\$\{([^}:]+)(?::-([^}]*))?\}')

            def replace_env_var(match: re.Match) -> str:
                var_name = match.group(1)
                default_value = match.group(2) if match.group(2) is not None else ""

                # Get environment variable
                env_value = os.environ.get(var_name)

                # If no default specified, return env value or empty string
                if match.group(2) is None:
                    return env_value if env_value is not None else ""

                # If default specified, use env value if non-empty, else default
                if env_value:
                    return env_value
                return default_value

            return pattern.sub(replace_env_var, config)
        else:
            return config

    def _validate_config(self) -> None:
        """Validate the loaded configuration.

        Raises:
            ValueError: If required sections are missing.
        """
        missing_sections = []
        for section in self.REQUIRED_SECTIONS:
            if section not in self.config:
                missing_sections.append(section)

        if missing_sections:
            raise ValueError(
                f"Missing required configuration sections: {missing_sections}"
            )

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by dot-notation key.

        Args:
            key: Dot-separated key path (e.g., 'llm.provider').
            default: Default value if key not found.

        Returns:
            The configuration value, or default if not found.

        Examples:
            >>> settings.get('llm.provider')
            'azure'
            >>> settings.get('llm.temperature', 0.7)
            0.7
        """
        keys = key.split(".")
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_section(self, section: str) -> Dict[str, Any]:
        """Get an entire configuration section.

        Args:
            section: Top-level section name.

        Returns:
            The configuration section as a dictionary.

        Raises:
            KeyError: If the section doesn't exist.
        """
        if section not in self.config:
            raise KeyError(f"Configuration section not found: {section}")
        return self.config[section]

    @property
    def llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration section.

        Returns:
            LLM configuration dictionary.
        """
        return self.get_section("llm")

    @property
    def embedding_config(self) -> Dict[str, Any]:
        """Get embedding configuration section.

        Returns:
            Embedding configuration dictionary.
        """
        return self.get_section("embedding")

    @property
    def vector_store_config(self) -> Dict[str, Any]:
        """Get vector store configuration section.

        Returns:
            Vector store configuration dictionary.
        """
        return self.get_section("vector_store")

    @property
    def retrieval_config(self) -> Dict[str, Any]:
        """Get retrieval configuration section.

        Returns:
            Retrieval configuration dictionary.
        """
        return self.get_section("retrieval", {})

    @property
    def reranker_config(self) -> Dict[str, Any]:
        """Get reranker configuration section.

        Returns:
            Reranker configuration dictionary.
        """
        return self.get_section("reranker", {})

    def __repr__(self) -> str:
        """String representation of Settings."""
        return f"Settings(config_path={self.config_path})"


# Global settings instance (lazy loaded)
_global_settings: Optional[Settings] = None


def load_settings(config_path: Optional[str] = None) -> Settings:
    """Load or get the global settings instance.

    This function implements a singleton pattern for settings.
    On first call, it loads the configuration. Subsequent calls
    return the cached instance.

    Args:
        config_path: Path to configuration file. Only used on first call.

    Returns:
        The Settings instance.

    Examples:
        >>> settings = load_settings()
        >>> provider = settings.get('llm.provider')
    """
    global _global_settings

    if _global_settings is None:
        _global_settings = Settings(config_path)

    return _global_settings


def reload_settings(config_path: Optional[str] = None) -> Settings:
    """Force reload the global settings instance.

    Args:
        config_path: Path to configuration file.

    Returns:
        The newly loaded Settings instance.
    """
    global _global_settings
    _global_settings = Settings(config_path)
    return _global_settings
