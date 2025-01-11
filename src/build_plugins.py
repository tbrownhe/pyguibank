import json
import py_compile
import shutil
import sys
from pathlib import Path

from loguru import logger

from core.plugins import load_plugin

# Define source and destination directories
SOURCE_DIR = Path("src/plugins")
DEST_DIR = Path("dist/plugins")
SERVER_DATA_DIR = Path("../pyguibank-server/data/plugins").resolve()


def compile_plugins():
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    SERVER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for plugin_file in SOURCE_DIR.glob("*.py"):
        if plugin_file.stem == "__init__":
            continue
        try:
            # Load metadata from the plugin
            _, _, metadata = load_plugin(plugin_file)

            # Plugin name based on internal metadata to ensure single source of truth
            plugin_name = metadata["PLUGIN_NAME"]
            version = metadata["VERSION"]
            py_version = f"{sys.version_info.major}{sys.version_info.minor}"
            compiled_name = f"{plugin_name}_v{version}_p{py_version}.pyc"
            compiled_path = DEST_DIR / compiled_name

            # Compile the plugin to a .pyc file
            py_compile.compile(plugin_file, cfile=compiled_path)

            # Copy to the server data/plugins directory for deployment
            shutil.copy2(compiled_path, SERVER_DATA_DIR)
            logger.success(f"Compiled: {plugin_file} -> {compiled_path}")
        except Exception as e:
            logger.error(f"Failed to compile {plugin_file}: {e}")


def generate_metadata():
    """
    Generate metadata for all .pyc files in server data dir
    Must be done here since .pyc files must be read by the same version of
    Python they were compiled with.
    """
    metadata_file = SERVER_DATA_DIR / "plugins_metadata.json"
    metadata_list = []
    for plugin_file in SERVER_DATA_DIR.glob("*.pyc"):
        try:
            # Get the metadata
            _, _, metadata = load_plugin(plugin_file)

            # Remove any secret sauce
            if "SEARCH_STRING" in metadata:
                del metadata["SEARCH_STRING"]

            # Add the filename
            metadata["FILENAME"] = plugin_file.name

            # Add to the list
            metadata_list.append(metadata)
        except Exception as e:
            print(f"Failed to extract metadata for {plugin_file}: {e}")

    with metadata_file.open("w") as f:
        json.dump(metadata_list, f, indent=2)

    logger.success(f"Created server metadata file {metadata_file}")


if __name__ == "__main__":
    compile_plugins()
    generate_metadata()
