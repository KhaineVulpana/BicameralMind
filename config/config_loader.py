"""Config loader for BicameralMind."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def save_config(config: Dict[str, Any], path: Optional[str] = None) -> None:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, default_flow_style=False, sort_keys=False)
