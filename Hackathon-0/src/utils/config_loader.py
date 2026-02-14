"""Utility for loading configuration from JSON files."""

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


def load_vault_config(config_path: str = "config/vault_config.json") -> Dict[str, Any]:
    """Load vault configuration from a JSON file.

    Args:
        config_path: Path to the JSON config file.

    Returns:
        Parsed configuration dictionary.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError:        If the file cannot be parsed as JSON or is not a dict.
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    try:
        with open(config_file, "r", encoding="utf-8") as fh:
            config = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in configuration file '{config_file}': {exc}") from exc

    if not isinstance(config, dict):
        raise ValueError(
            f"Configuration file '{config_file}' must contain a JSON object, "
            f"got {type(config).__name__}"
        )

    logger.debug(f"Loaded configuration from '{config_file}' ({len(config)} keys)")
    return config
