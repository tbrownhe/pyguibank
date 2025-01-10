import shutil
import sys
from pathlib import Path
from loguru import logger
from core.settings import settings


def initialize_plugins():
    """
    Copies bundled plugins to the user plugin directory if they don't exist.
    """
    plugin_bundled_dir = (
        Path("plugins") if hasattr(sys, "_MEIPASS") else Path("dist/plugins")
    ).resolve()

    try:
        if not settings.plugin_dir.exists():
            logger.debug(f"Plugins directory does not exist yet.")
            if not plugin_bundled_dir.exists():
                settings.plugin_dir.mkdir(parents=True, exist_ok=True)
                logger.debug(
                    f"Bundled plugins not found in {plugin_bundled_dir}, skipping"
                )
            else:
                shutil.copytree(plugin_bundled_dir, settings.plugin_dir)
                logger.debug(
                    f"Copied bundled plugins from {plugin_bundled_dir} to {settings.plugin_dir}"
                )
    except Exception as e:
        logger.error(f"Failed to initialize plugins: {e}")
