import shutil
import sys
from pathlib import Path
from loguru import logger
from core.plugins import PLUGIN_DIR


def initialize_plugins():
    """
    Copies bundled plugins to the user plugin directory if they don't exist.
    PLUGIN_DIR is defined relative to CONFIG_PATH, which is platform-dependent.
    """
    # Get the location of the bundled plugins
    plugin_bundled_dir = (
        Path("plugins") if hasattr(sys, "_MEIPASS") else Path("dist/plugins")
    ).resolve()

    # Copy the bundled plugins to the user's PLUGIN_DIR
    try:
        if not PLUGIN_DIR.exists():
            logger.debug(f"Plugins directory does not exist yet.")
            if not plugin_bundled_dir.exists():
                PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
                logger.debug(
                    f"Bundled plugins not found in {plugin_bundled_dir}, skipping"
                )
            else:
                shutil.copytree(plugin_bundled_dir, PLUGIN_DIR)
                logger.debug(
                    f"Copied bundled plugins from {plugin_bundled_dir} to {PLUGIN_DIR}"
                )
    except Exception as e:
        logger.error(f"Failed to initialize plugins: {e}")
