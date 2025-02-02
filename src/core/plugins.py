import importlib.util
import os
import time
from pathlib import Path

import requests
from loguru import logger
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QProgressDialog

from core.interfaces import IParser, class_variables, validate_parser
from core.settings import settings


def load_plugin(plugin_file: Path) -> tuple[str, IParser, dict[str, str]]:
    """
    Dynamically load the Parser class from a plugin module, validate it, and retrieve metadata.
    plugin_file.name like 'pdf_citicc_v0.1.0.pyc'
    """
    # Load the module from file
    plugin_name = plugin_file.stem
    spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
    if not spec or not spec.loader:
        raise ImportError(f"Cannot load module from {plugin_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Ensure this module contains a Parser(IParser)
    ParserClass = getattr(module, "Parser", None)
    if not ParserClass:
        raise ValueError(f"No 'Parser' class found in {plugin_file}")
    if not isinstance(ParserClass, IParser):
        raise TypeError(f"Plugin {plugin_name} must implement IParser")

    # Validate that the plugin overrides required class variables (metadata)
    required_variables = class_variables(IParser)
    try:
        validate_parser(ParserClass, required_variables)
    except Exception as e:
        raise ImportError(f"Failed to load plugin {plugin_name}: {e}")

    # Extract plugin metadata
    metadata = {var: getattr(ParserClass, var) for var in required_variables}

    return plugin_name, ParserClass, metadata


class PluginManager:
    def __init__(self):
        self.plugins = None
        self.metadata = None

    def load_plugins(self):
        """
        Load all plugins in the specified path.
        """
        self.plugins = {}
        self.metadata = {}

        success = 0
        for plugin_file in settings.plugin_dir.glob("*.pyc"):
            # Retrieve the Parser(Iparser) class from the plugin and store it
            try:
                plugin_name, ParserClass, metadata = load_plugin(plugin_file)
                self.plugins[plugin_name] = ParserClass
                self.metadata[plugin_name] = metadata
                success += 1
            except Exception as e:
                logger.error(f"Failed to load {plugin_file}: {e}")

        if success > 0:
            logger.success(f"Loaded {success} plugins")

        # Build the set of supported file extensions
        self.suffixes = sorted(set(plugin["SUFFIX"] for plugin in self.metadata.values()))

    def get_parser(self, plugin_name: str):
        """
        Retrieve a specific parser class from the preloaded plugins.
        """
        ParserClass = self.plugins.get(plugin_name)
        if not ParserClass:
            raise ImportError(f"Plugin '{plugin_name}' not loaded.")
        return ParserClass

    def list_plugins(self):
        for plugin_name, ParserClass in self.plugins.items():
            print(plugin_name, ParserClass)

    def list_metadata(self):
        """
        Display validated metadata for all plugins.
        """
        for plugin_name, metadata in self.metadata.items():
            print(f"Plugin: {plugin_name}")
            for key, value in metadata.items():
                print(f"  {key}: {value}")


def server_plugin_metadata():
    """
    Fetches the list of available plugins from the server.
    """
    try:
        response = requests.get(f"{settings.server_url}/plugins")
        response.raise_for_status()  # Raise an exception for HTTP errors
        plugins = response.json()  # Parse JSON response
        return plugins
    except requests.RequestException as e:
        logger.error(f"Error fetching plugin list: {e}")
        raise ConnectionError("Unable to establish connection to server.")


def download_plugin(plugin_filename: str):
    """
    Downloads a specific plugin from the server.

    :param file_type: Type of the plugin (e.g., 'type1')
    :param plugin_name: Name of the plugin (e.g., 'plugin1')
    """
    settings.plugin_dir.mkdir(parents=True, exist_ok=True)
    save_path = settings.plugin_dir / plugin_filename
    try:
        url = f"{settings.server_url}/plugins/{plugin_filename}/{settings.api_token}"
        with requests.get(url, stream=True) as response:
            response.raise_for_status()
            with save_path.open("wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
        logger.success(f"Downloaded new plugin {plugin_filename}")
    except requests.RequestException as e:
        logger.error(f"Error downloading plugin {plugin_filename}: {e}")
        raise


def delete_local_plugin(plugin_filename: str):
    delete_path = settings.plugin_dir / plugin_filename
    try:
        os.remove(delete_path)
        logger.success(f"Removed old plugin {plugin_filename}")
    except Exception as e:
        logger.error(f"Error removing plugin {plugin_filename}: {e}")
        raise


def compare_plugins(local_plugins: list[dict], server_plugins: list[dict]) -> list[dict]:
    new_plugins = []
    obsolete_plugins = []
    for server_plugin in server_plugins:
        plugin_name = server_plugin["PLUGIN_NAME"]
        local_plugin = next(
            (lp for lp in local_plugins if lp["PLUGIN_NAME"] == plugin_name),
            None,
        )
        if local_plugin is None or local_plugin["VERSION"] < server_plugin["VERSION"]:
            new_plugins.append(server_plugin)
            if local_plugin:
                obsolete_plugins.append(local_plugin)
    return new_plugins, obsolete_plugins


def sync_plugins(local_plugins: list[dict], server_plugins: list[dict], progress=False, parent=None):
    """For each plugin on the server, downloads plugin if missing from local,
    and updates old plugins if they exist. Ignores plugins on user's machine that
    are not on the server in case something weird happens.

    Args:
        local_plugins (list[dict]): Local plugin metadata
        server_plugins (list[dict]): Remote plugin metadata
    """
    new_plugins, obsolete_plugins = compare_plugins(local_plugins, server_plugins)

    if progress:
        dialog = QProgressDialog(
            "Updating Plugins",
            "Cancel",
            0,
            len(new_plugins) + len(obsolete_plugins),
            parent,
        )
        dialog.setMinimumWidth(400)
        dialog.setWindowTitle("Updating Plugins")
        dialog.setWindowModality(Qt.WindowModal)
        dialog.setMinimumDuration(100)
        dialog.setValue(0)
        dialog.show()
        QApplication.processEvents()

    for plugin in new_plugins:
        plugin_name = plugin["PLUGIN_NAME"]
        dialog.setLabelText(f"Downloading new {plugin_name}")
        try:
            download_plugin(plugin["FILENAME"])
            if progress:
                dialog.setValue(dialog.value() + 1)
                QApplication.processEvents()
        except Exception as e:
            logger.error(f"Failed to download new plugin {plugin_name}: {e}")
            raise

    for plugin in obsolete_plugins:
        plugin_name = plugin["PLUGIN_NAME"]
        dialog.setLabelText(f"Removing obsolete {plugin_name}")
        try:
            delete_local_plugin(plugin["FILENAME"])
            time.sleep(0.2)
            if progress:
                dialog.setValue(dialog.value() + 1)
        except Exception as e:
            logger.error(f"Failed to remove obsolete plugin {plugin_name}: {e}")
            raise

    if progress:
        dialog.close()


def get_plugin_lists(plugin_manager: PluginManager) -> tuple[list, list]:
    """Silently downloads any new updated plugins to local machine

    Args:
        plugin_manager (PluginManager): PluginManager

    Returns:
        tuple[list, list]: local_plugins, server_plugins
    """
    local_plugins = [plugin for plugin in plugin_manager.metadata.values()]
    server_plugins = server_plugin_metadata()
    return local_plugins, server_plugins


def check_for_plugin_updates(plugin_manager: PluginManager, parent=None) -> bool:
    """Silently downloads any new updated plugins to local machine

    Args:
        plugin_manager (PluginManager): PluginManager

    Returns:
        bool: Whether plugins were updated
    """
    local_plugins = [plugin for plugin in plugin_manager.metadata.values()]
    server_plugins = server_plugin_metadata()
    new_plugins, _ = compare_plugins(local_plugins, server_plugins)
    if new_plugins:
        sync_plugins(local_plugins, server_plugins, progress=True, parent=parent)
        return True
    return False
