import importlib.util
from pathlib import Path

import requests
from loguru import logger

from core.interfaces import IParser, validate_parser, class_variables
from core.settings import settings


def get_plugins():
    """
    Fetches the list of available plugins from the server.
    """
    try:
        response = requests.get(f"{settings.server_url}/plugins")
        response.raise_for_status()  # Raise an exception for HTTP errors
        plugins = response.json()  # Parse JSON response
        return plugins
    except requests.RequestException as e:
        print(f"Error fetching plugins: {e}")
        return []


def download_plugin(file_type: str, plugin_name: str, save_path: Path):
    """
    Downloads a specific plugin from the server.

    :param file_type: Type of the plugin (e.g., 'type1')
    :param plugin_name: Name of the plugin (e.g., 'plugin1')
    :param save_path: Local path to save the downloaded file
    """
    try:
        url = f"{settings.server_url}/plugins/{file_type}/{plugin_name}"
        with requests.get(url, stream=True) as response:
            response.raise_for_status()
            with save_path.open("wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
        print(f"Plugin {plugin_name} downloaded successfully to {save_path}")
    except requests.RequestException as e:
        print(f"Error downloading plugin {plugin_name}: {e}")


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
