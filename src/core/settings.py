"""Configuration loader for RAG MCP framework.

This module provides a centralized configuration management system that loads
settings from config/settings.yaml and provides typed access to configuration values.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Union
import yaml


class Settings:
    """Centralized configuration manager for RAG MCP.

    Loads configuration from config/settings.yaml and provides access to
    configuration values with environment variable substitution.

    Usage:
        settings = Settings()
        llm_model = settings.llm.model
        vector_store_path = settings.vector_store.chroma.path
    """

    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        project_root: Optional[Union[str, Path]] = None,
    ):
        """Initialize Settings by loading configuration from YAML file.

        Args:
            config_path: Path to settings.yaml. Defaults to config/settings.yaml
            project_root: Project root directory. Defaults to auto-detection.
        """
        self._project_root = self._find_project_root(project_root)
        self._config_path = self._resolve_config_path(config_path)
        self._config: Dict[str, Any] = self._load_config()
        self._substitute_env_vars()

    def _find_project_root(self, project_root: Optional[Union[str, Path]]) -> Path:
        """Find the project root directory.

        Args:
            project_root: Explicit project root path or None for auto-detection.

        Returns:
            Path to project root directory.
        """
        if project_root is not None:
            return Path(project_root).resolve()

        # Auto-detect by looking for pyproject.toml or .git
        current = Path.cwd()
        while current != current.parent:
            if (current / "pyproject.toml").exists() or (current / ".git").exists():
                return current
            current = current.parent

        # Fallback to current directory
        return Path.cwd()

    def _resolve_config_path(self, config_path: Optional[Union[str, Path]]) -> Path:
        """Resolve the configuration file path.

        Args:
            config_path: Explicit config path or None for default.

        Returns:
            Path to configuration file.

        Raises:
            FileNotFoundError: If config file doesn't exist.
        """
        if config_path is not None:
            path = Path(config_path).resolve()
        else:
            path = self._project_root / "config" / "settings.yaml"

        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        return path

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file.

        Returns:
            Configuration dictionary.
        """
        with open(self._config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _substitute_env_vars(self) -> None:
        """Substitute environment variable placeholders in configuration.

        Replaces values like ${VAR_NAME} or ${VAR_NAME:default} with
        the corresponding environment variable value.
        """
        self._config = self._substitute_dict(self._config)

    def _substitute_dict(self, data: Any) -> Any:
        """Recursively substitute environment variables in a dictionary.

        Args:
            data: Data structure to process.

        Returns:
            Data structure with substituted values.
        """
        if isinstance(data, dict):
            return {k: self._substitute_dict(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._substitute_dict(item) for item in data]
        elif isinstance(data, str):
            return self._substitute_string(data)
        return data

    def _substitute_string(self, value: str) -> str:
        """Substitute environment variables in a string.

        Args:
            value: String possibly containing ${VAR} or ${VAR:default}.

        Returns:
            String with substituted environment variables.
        """
        import re

        pattern = r'\$\{([^:}]+)(?::([^}]*))?\}'

        def replacer(match):
            var_name = match.group(1)
            default = match.group(2) if match.group(2) is not None else ""
            return os.getenv(var_name, default)

        return re.sub(pattern, replacer, value)

    @property
    def config(self) -> Dict[str, Any]:
        """Get the raw configuration dictionary."""
        return self._config.copy()

    @property
    def project_root(self) -> Path:
        """Get the project root directory."""
        return self._project_root

    @property
    def config_path(self) -> Path:
        """Get the configuration file path."""
        return self._config_path

    # LLM Configuration
    @property
    def llm(self) -> "_SectionProxy":
        """Access LLM configuration section."""
        return _SectionProxy(self._config.get("llm", {}))

    @property
    def vision_llm(self) -> "_SectionProxy":
        """Access Vision LLM configuration section."""
        return _SectionProxy(self._config.get("vision_llm", {}))

    # Embedding Configuration
    @property
    def embedding(self) -> "_SectionProxy":
        """Access Embedding configuration section."""
        return _SectionProxy(self._config.get("embedding", {}))

    # Vector Store Configuration
    @property
    def vector_store(self) -> "_SectionProxy":
        """Access Vector Store configuration section."""
        return _SectionProxy(self._config.get("vector_store", {}))

    # Splitter Configuration
    @property
    def splitter(self) -> "_SectionProxy":
        """Access Splitter configuration section."""
        return _SectionProxy(self._config.get("splitter", {}))

    # Retrieval Configuration
    @property
    def retrieval(self) -> "_SectionProxy":
        """Access Retrieval configuration section."""
        return _SectionProxy(self._config.get("retrieval", {}))

    # Reranker Configuration
    @property
    def reranker(self) -> "_SectionProxy":
        """Access Reranker configuration section."""
        return _SectionProxy(self._config.get("reranker", {}))

    # Ingestion Configuration
    @property
    def ingestion(self) -> "_SectionProxy":
        """Access Ingestion configuration section."""
        return _SectionProxy(self._config.get("ingestion", {}))

    # Evaluation Configuration
    @property
    def evaluation(self) -> "_SectionProxy":
        """Access Evaluation configuration section."""
        return _SectionProxy(self._config.get("evaluation", {}))

    # Observability Configuration
    @property
    def observability(self) -> "_SectionProxy":
        """Access Observability configuration section."""
        return _SectionProxy(self._config.get("observability", {}))

    # MCP Server Configuration
    @property
    def mcp_server(self) -> "_SectionProxy":
        """Access MCP Server configuration section."""
        return _SectionProxy(self._config.get("mcp_server", {}))

    # Cache Configuration
    @property
    def cache(self) -> "_SectionProxy":
        """Access Cache configuration section."""
        return _SectionProxy(self._config.get("cache", {}))

    # Environment Configuration
    @property
    def env(self) -> "_SectionProxy":
        """Access Environment configuration section."""
        return _SectionProxy(self._config.get("env", {}))

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key path (e.g., 'llm.provider').

        Args:
            key: Dot-separated key path.
            default: Default value if key not found.

        Returns:
            Configuration value or default.
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def reload(self) -> None:
        """Reload configuration from file."""
        self._config = self._load_config()
        self._substitute_env_vars()


class _SectionProxy:
    """Proxy for accessing configuration sections with attribute and item access.

    Provides convenient access to nested configuration values through both
    attribute (section.llm.provider) and item (section['llm']['provider']) syntax.
    """

    def __init__(self, data: Dict[str, Any]):
        """Initialize the proxy with configuration data.

        Args:
            data: Configuration dictionary for this section.
        """
        self._data = data or {}

    def __getattr__(self, name: str) -> Any:
        """Get a configuration value as an attribute.

        Args:
            name: Configuration key name.

        Returns:
            Configuration value, wrapped in _SectionProxy if it's a dict.
        """
        if name.startswith("_"):
            raise AttributeError(name)

        value = self._data.get(name)

        if isinstance(value, dict):
            return _SectionProxy(value)
        return value

    def __getitem__(self, key: str) -> Any:
        """Get a configuration value by key.

        Args:
            key: Configuration key.

        Returns:
            Configuration value, wrapped in _SectionProxy if it's a dict.
        """
        value = self._data.get(key)

        if isinstance(value, dict):
            return _SectionProxy(value)
        return value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with default.

        Args:
            key: Configuration key.
            default: Default value if key not found.

        Returns:
            Configuration value or default.
        """
        return self._data.get(key, default)

    def as_dict(self) -> Dict[str, Any]:
        """Get the raw dictionary for this section."""
        return self._data.copy()

    def keys(self):
        """Return configuration keys."""
        return self._data.keys()

    def values(self):
        """Return configuration values."""
        return self._data.values()

    def items(self):
        """Return configuration items."""
        return self._data.items()

    def __contains__(self, key: str) -> bool:
        """Check if a configuration key exists."""
        return key in self._data

    def __repr__(self) -> str:
        """String representation of the section."""
        keys = list(self._data.keys())[:5]
        more = "..." if len(self._data) > 5 else ""
        return f"_SectionProxy({keys}{more})"


# Global settings instance
_global_settings: Optional[Settings] = None
_global_config_path: Optional[Path] = None


def get_settings(
    config_path: Optional[Union[str, Path]] = None,
    reload: bool = False,
) -> Settings:
    """Get the global Settings instance.

    Args:
        config_path: Path to config file (only used on first call).
        reload: Whether to reload the configuration.

    Returns:
        Global Settings instance.
    """
    global _global_settings, _global_config_path

    if config_path is not None:
        _global_config_path = Path(config_path).resolve()

    if _global_settings is None or reload:
        _global_settings = Settings(config_path=_global_config_path)

    return _global_settings


def reset_settings() -> None:
    """Reset the global settings instance (useful for testing)."""
    global _global_settings
    _global_settings = None


__all__ = ["Settings", "get_settings", "reset_settings"]
