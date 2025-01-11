import py_compile
from pathlib import Path

from loguru import logger

from core.plugins import load_plugin

# Define source and destination directories
SOURCE_DIR = Path("src/plugins")
DEST_DIR = Path("dist/plugins")


def compile_plugins():
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    for plugin_file in SOURCE_DIR.glob("*.py"):
        if plugin_file.stem == "__init__":
            continue
        try:
            # Load metadata from the plugin
            _, _, metadata = load_plugin(plugin_file)
            version = metadata["VERSION"]
            compiled_name = f"{plugin_file.stem}_v{version}.pyc"
            compiled_path = DEST_DIR / compiled_name

            # Compile the plugin to a .pyc file
            py_compile.compile(plugin_file, cfile=compiled_path)
            logger.success(f"Compiled: {plugin_file} -> {compiled_path}")
        except Exception as e:
            logger.error(f"Failed to compile {plugin_file}: {e}")


if __name__ == "__main__":
    compile_plugins()
