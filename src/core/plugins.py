import importlib.util
import os
from pathlib import Path

import requests
from loguru import logger
from PyQt5.QtCore import QThread, pyqtSignal

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

        for plugin_file in settings.plugin_dir.glob("*.pyc"):
            # Retrieve the Parser(Iparser) class from the plugin and store it
            try:
                plugin_name, ParserClass, metadata = load_plugin(plugin_file)
                self.plugins[plugin_name] = ParserClass
                self.metadata[plugin_name] = metadata
                logger.success(f"Loaded plugin: {plugin_file}")
            except Exception as e:
                logger.error(f"Failed to load {plugin_file}: {e}")

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
        logger.error(f"Error fetching plugins: {e}")
        return []


def compare_plugins(local_plugins: list[dict], server_plugins: list[dict]):
    """
    Compare server plugins with local plugins to determine updates and new plugins.

    Args:
        server_plugins (list[dict]): Metadata of plugins available on the server.
        local_plugins (list[dict]): Metadata of plugins available locally.

    Returns:
        tuple[list[dict], list[dict]]: (new_plugins, updated_plugins)
    """
    local_dict = {plugin["PLUGIN_NAME"]: plugin["VERSION"] for plugin in local_plugins}

    new_plugins = []
    updated_plugins = []

    for plugin in server_plugins:
        key = plugin["PLUGIN_NAME"]
        if key not in local_dict:
            new_plugins.append(plugin)
        elif plugin["VERSION"] > local_dict[key]:
            updated_plugins.append(plugin)

    return new_plugins, updated_plugins


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


def sync_plugins(local_plugins: list[dict], server_plugins: list[dict]):
    """For each plugin on the server, downloads plugin if missing from local,
    and updates old plugins if they exist. Ignores plugins on user's machine that
    are not on the server in case something weird happens.

    Args:
        local_plugins (list[dict]): Local plugin metadata
        server_plugins (list[dict]): Remote plugin metadata
    """
    for server_plugin in server_plugins:
        plugin_name = server_plugin["PLUGIN_NAME"]
        try:
            local_plugin = next(
                (lp for lp in local_plugins if lp["PLUGIN_NAME"] == plugin_name),
                None,
            )
            if (
                local_plugin is None
                or local_plugin["VERSION"] < server_plugin["VERSION"]
            ):
                download_plugin(server_plugin["FILENAME"])
                if local_plugin:
                    delete_local_plugin(local_plugin["FILENAME"])
        except Exception as e:
            logger.error(f"Failed to sync plugin {plugin_name}: {e}")
            raise


def check_for_plugin_updates(plugin_manager: PluginManager) -> bool:
    """Downloads any new updated plugins to local machine

    Args:
        plugin_manager (PluginManager): PluginManager

    Returns:
        bool: Whether plugins were updated
    """
    local_plugins = [plugin for plugin in plugin_manager.metadata.values()]
    server_plugins = server_plugin_metadata()
    new_plugins, updated_plugins = compare_plugins(local_plugins, server_plugins)
    if new_plugins or updated_plugins:
        sync_plugins(local_plugins, server_plugins)
        return True
    return False


class PluginUpdateThread(QThread):
    """Checks for plugins in a separate thread"""

    update_complete = pyqtSignal(bool, str, PluginManager)

    def __init__(self, plugin_manager: PluginManager):
        super().__init__()
        self.plugin_manager = plugin_manager

    def run(self):
        try:
            updated = check_for_plugin_updates(self.plugin_manager)
            if updated:
                self.update_complete.emit(
                    True, "Plugins have been updated.", self.plugin_manager
                )
            else:
                self.update_complete.emit(True, "", self.plugin_manager)
        except Exception as e:
            self.update_complete.emit(
                False, f"Plugin update Failed: {e}", self.plugin_manager
            )
