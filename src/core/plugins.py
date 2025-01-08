import importlib.util
from pathlib import Path
from core.config import CONFIG_PATH

PLUGIN_DIR = (CONFIG_PATH.parent / "plugins").resolve()


class PluginManager:
    def __init__(self):
        self.plugins = None

    def load_plugins(self, plugin_dir: Path = PLUGIN_DIR):
        """
        Load all plugins in the specified path.
        """
        self.plugins = {}
        for plugin_file in plugin_dir.glob("**/*.pyc"):
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
