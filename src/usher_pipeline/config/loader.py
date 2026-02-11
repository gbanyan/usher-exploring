"""Configuration loading with YAML parsing and validation."""

from pathlib import Path
from typing import Any

import pydantic_yaml

from .schema import PipelineConfig


def load_config(config_path: Path | str) -> PipelineConfig:
    """
    Load and validate pipeline configuration from YAML file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        Validated PipelineConfig instance

    Raises:
        FileNotFoundError: If config file doesn't exist
        pydantic.ValidationError: If config is invalid
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # Read YAML file
    with open(config_path, "r") as f:
        yaml_content = f.read()

    # Parse and validate with Pydantic
    config = pydantic_yaml.parse_yaml_raw_as(PipelineConfig, yaml_content)

    return config


def load_config_with_overrides(
    config_path: Path | str,
    overrides: dict[str, Any],
) -> PipelineConfig:
    """
    Load config from YAML and apply dictionary overrides.

    Useful for CLI flags that override config file values.

    Args:
        config_path: Path to YAML configuration file
        overrides: Dictionary of values to override (nested keys supported)

    Returns:
        Validated PipelineConfig with overrides applied

    Raises:
        FileNotFoundError: If config file doesn't exist
        pydantic.ValidationError: If final config is invalid
    """
    # Load base config
    config = load_config(config_path)

    # Convert to dict, apply overrides, re-validate
    config_dict = config.model_dump()

    # Apply overrides (simple flat merge for now)
    for key, value in overrides.items():
        if "." in key:
            # Handle nested keys like "api.rate_limit_per_second"
            parts = key.split(".")
            target = config_dict
            for part in parts[:-1]:
                target = target[part]
            target[parts[-1]] = value
        else:
            config_dict[key] = value

    # Re-validate with overrides applied
    config = PipelineConfig.model_validate(config_dict)

    return config
