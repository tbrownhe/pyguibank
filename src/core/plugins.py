import importlib.util
import os
from pathlib import Path

import requests
from loguru import logger

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


"""
if True:
    plugins = get_plugins()
    if plugins:
        print("Available Plugins:")
        for i, plugin in enumerate(plugins):
            print("Plugin", i + 1)
            for key, value in plugin.items():
                print(f"  {key}: {value}")
    else:
        print("No plugins available or an error occurred.")
else:
    file_type, plugin_name, save_path = (
        "pdf",
        "capitaloneauto",
        Path("capitaloneauto.pyc"),
    )
    download_plugin(file_type, plugin_name, save_path)
"""


class PluginManager:
    def __init__(self):
        self.plugins = None

    def load_plugins(self):
        """
        Load all plugins in the specified path.
        """
        self.plugins = {}
        for plugin_file in settings.plugin_dir.glob("**/*.pyc"):
            module_name = plugin_file.stem.split(".")[0]
            if module_name == "__init__":
                continue
            package = (
                plugin_file.parents[1].stem
                if plugin_file.parents[0].stem == "__pycache__"
                else plugin_file.parents[0].stem
            )
            plugin_name = ".".join([package, module_name])
            module = self.load_module_from_file(plugin_name, plugin_file)
            if module:
                self.plugins[plugin_name] = module

    def load_module_from_file(self, plugin_name: str, filepath: Path):
        """
        Load a Python module from a .pyc file.
        """
        try:
            spec = importlib.util.spec_from_file_location(plugin_name, filepath)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                # sys.modules[plugin_name] = module
                spec.loader.exec_module(module)
                return module
        except Exception as e:
            print(f"Failed to load plugin {plugin_name}: {e}")
        return None

    def get_parser(self, parser_name: str, class_name: str):
        """
        Retrieve a specific parser class from the preloaded plugins.
        """
        module = self.plugins.get(parser_name)
        if not module:
            raise ImportError(f"Plugin '{parser_name}' not loaded.")
        return getattr(module, class_name, None)

    def list_plugins(self):
        for name, module in self.plugins.items():
            print(name, module)
