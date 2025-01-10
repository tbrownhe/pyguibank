import importlib.util
from pathlib import Path
from typing import Optional

import requests
from loguru import logger
from pydantic import BaseModel, Field, ValidationError, field_validator

from core.interfaces import IParser
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


class PluginMetadata(BaseModel):
    plugin_name: str
    statement_type: str
    version: str
    description: Optional[str] = Field(
        "", description="A short description of the plugin."
    )
    search_string: str
    file_path: str

    # Validator to reject empty string values
    @field_validator(
        "plugin_name", "statement_type", "version", "search_string", mode="before"
    )
    def no_error_or_empty(cls, value, field):
        """
        Ensure no field is an empty string.
        """
        # field_name = field.field_name
        if value == "":
            raise ValueError(f"Field '{field.field_name}' cannot be empty.")
        return value

    # Validator to set default description
    @field_validator("description", mode="before")
    def default_description(cls, value):
        """
        If description is empty, set a default value.
        """
        return value or "No description provided."


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

        for plugin_file in settings.plugin_dir.glob("**/*.pyc"):
            # plugin_name like 'pdf.citibank'
            module_name = plugin_file.stem
            if module_name.split(".")[0] == "__init__":
                continue
            file_type = plugin_file.parent.name
            plugin_name = ".".join([file_type, module_name])

            # Retrieve the Parser(Iparser) class from the plugin and store it
            ParserClass, metadata = self.load_module_from_file(plugin_name, plugin_file)
            if ParserClass:
                self.plugins[plugin_name] = ParserClass
                self.metadata[plugin_name] = metadata

    def load_module_from_file(self, plugin_name: str, plugin_file: Path):
        """
        Load a Python module from a .pyc file.
        """
        try:
            # Load the module and spec
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
            if not spec or not spec.loader:
                raise ImportError(f"Cannot load module from {plugin_file}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Get the class called Parser(IParser) from the module
            ParserClass = getattr(module, "Parser", None)
            if not ParserClass:
                raise ValueError(f"Parser class not found in {plugin_file}")
            if not isinstance(ParserClass, IParser):
                raise TypeError(f"{ParserClass} must implement IParser")

            # Extract and validate the metadata
            metadata = {
                "plugin_name": plugin_name,
                "statement_type": getattr(ParserClass, "STATEMENT_TYPE", ""),
                "version": getattr(ParserClass, "VERSION", ""),
                "description": getattr(ParserClass, "DESCRIPTION", ""),
                "search_string": getattr(ParserClass, "SEARCH_STRING", ""),
                "file_path": str(plugin_file),
            }

            # Validate metadata
            metadata = PluginMetadata(**metadata)

            return ParserClass, metadata
        except ValidationError as e:
            logger.error(f"Validation error for plugin {plugin_name}: {e}")
            return None, None
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_name}: {e}")
            return None, None

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
