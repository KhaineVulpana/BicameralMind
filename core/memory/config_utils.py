"""Configuration helpers for cross-hemisphere features."""

from typing import Any, Dict


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge two dicts without mutating inputs."""
    result: Dict[str, Any] = {}
    base = base or {}
    override = override or {}

    for key in set(base) | set(override):
        left = base.get(key)
        right = override.get(key)
        if isinstance(left, dict) and isinstance(right, dict):
            result[key] = deep_merge(left, right)
        elif right is not None:
            result[key] = right
        else:
            result[key] = left

    return result


def get_cross_hemisphere_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Return merged cross-hemisphere config from supported locations."""
    config = config or {}
    memory_cfg = config.get("memory", {}) or {}
    procedural_cfg = config.get("procedural_memory", {}) or {}

    from_memory = memory_cfg.get("cross_hemisphere", {}) or {}
    from_procedural = procedural_cfg.get("cross_hemisphere", {}) or {}

    # procedural_memory overrides memory if both are set
    return deep_merge(from_memory, from_procedural)
