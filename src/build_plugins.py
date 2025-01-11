import importlib.util
import py_compile
from pathlib import Path

from loguru import logger

from core.interfaces import IParser

# Define source and destination directories
SOURCE_DIR = Path("src/plugins")
DEST_DIR = Path("dist/plugins")


def get_required_class_variables(cls):
    """
    Retrieve all required class variable names from the interface.
    """
    return [
        name
        for name in dir(cls)
        if not callable(getattr(cls, name))
        and not name.startswith("_")
        and isinstance(name, str)
    ]


def validate_parser_class(parser_class, required_variables):
    """
    Validate that all required class variables in the parser are non-empty strings.
    """
    errors = []
    for var_name in required_variables:
        value = getattr(parser_class, var_name, None)
        if not isinstance(value, str) or not value.strip():
            errors.append(
                f"Variable '{var_name}' is missing or invalid (value: {value!r})"
            )
    if errors:
        raise ValueError(
            f"Validation errors in parser '{parser_class.__name__}':\n"
            + "\n".join(errors)
        )


def get_parser_metadata(plugin_file: Path):
    """
    Dynamically load the Parser class from a plugin module, validate it, and retrieve metadata.
    """
    spec = importlib.util.spec_from_file_location(plugin_file.stem, plugin_file)
    if not spec or not spec.loader:
        raise ImportError(f"Cannot load module from {plugin_file}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    ParserClass = getattr(module, "Parser", None)
    if not ParserClass:
        raise ValueError(f"No 'Parser' class found in {plugin_file}")
    if not isinstance(ParserClass, IParser):
        raise TypeError(f"Plugin {plugin_file.stem} must implement IParser")

    # Validate required variables
    required_variables = get_required_class_variables(IParser)
    validate_parser_class(ParserClass, required_variables)

    # Extract metadata
    metadata = {var: getattr(ParserClass, var) for var in required_variables}
    return metadata


def compile_plugins():
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    for plugin_file in SOURCE_DIR.glob("*.py"):
        if plugin_file.stem == "__init__":
            continue
        try:
            # Load metadata from the plugin
            metadata = get_parser_metadata(plugin_file)
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
