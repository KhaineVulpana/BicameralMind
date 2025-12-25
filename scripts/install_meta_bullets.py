"""Install meta-bullets into procedural memory.

This script installs the base set of meta-bullets that define hemisphere
cognitive styles. These are used by the HemisphereClassifier to determine
where new bullets should be assigned.

Run this once during system setup or when meta-bullets need updating.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
from loguru import logger
from core.memory import ProceduralMemory
from core.memory.meta_bullets import install_meta_bullets, check_meta_bullets_installed


def main():
    """Install meta-bullets to procedural memory."""

    # Load config
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    logger.info("Initializing procedural memory...")
    memory = ProceduralMemory(config)

    # Check if already installed
    if check_meta_bullets_installed(memory):
        logger.warning("Meta-bullets appear to already be installed.")
        response = input("Reinstall anyway? (y/N): ")
        if response.lower() != 'y':
            logger.info("Skipping installation.")
            return

    # Install meta-bullets
    logger.info("Installing meta-bullets...")
    result = install_meta_bullets(memory)

    # Report results
    logger.success(f"Installation complete!")
    logger.info(f"  Total meta-bullets: {result['total']}")
    logger.info(f"  Left hemisphere patterns: {result['left_patterns']}")
    logger.info(f"  Right hemisphere patterns: {result['right_patterns']}")
    logger.info(f"  Ambiguous handlers: {result['ambiguous_handlers']}")

    # Verify installation
    logger.info("Verifying installation...")
    if check_meta_bullets_installed(memory):
        logger.success("Verification passed - meta-bullets are accessible")
    else:
        logger.error("Verification failed - meta-bullets not found")
        sys.exit(1)


if __name__ == "__main__":
    main()
