"""Infrastructure utilities for configuration and registry stubs."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv

from .storage_registry import StorageRegistry

CONFIG_ENV_VAR = "CONFIG_PATH"
DEFAULT_CONFIG_PATH = Path("config/default.yaml")


def load_config() -> Dict[str, Any]:
    """Load application configuration with environment overrides.

    Order:
    1. Load `.env` to populate environment variables.
    2. Read the default configuration file.
    3. Optionally apply overrides from CONFIG_PATH if it is set and exists.
    """

    load_dotenv()

    base_config = _read_config_file(DEFAULT_CONFIG_PATH)
    override_path = os.getenv(CONFIG_ENV_VAR)

    if override_path:
        override_file = Path(override_path)
        if override_file.exists():
            override_config = _read_config_file(override_file)
            return _merge_dicts(base_config, override_config)

    return base_config


def _read_config_file(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        content = yaml.safe_load(file) or {}
    return content


def _merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged

