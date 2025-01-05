from core.utils import PluginManager
from pathlib import Path


def test_plugin_manager(plugin_dir: Path, fpath: Path, entry_point: str):
    from core.utils import PDFReader

    # Initialize PluginManager and preload plugins
    plugin_manager = PluginManager()

    plugin_manager.load_plugins(plugin_dir)

    # Display the loaded plugins
    for name, module in plugin_manager.plugins.items():
        print(name, module)
    print("")

    # Get the parser class from the plugin
    parser_name, class_name = entry_point.split(":")
    ParserClass = plugin_manager.get_parser(parser_name, class_name)
    if not ParserClass:
        raise ImportError(f"Class '{class_name}' not found in plugin '{parser_name}'.")

    parser_instance = ParserClass()

    # Parse the PDF
    with PDFReader(fpath) as reader:
        statement = parser_instance.parse(reader)

    # Print the statement dataclass
    print(statement)


if __name__ == "__main__":
    plugin_dir = Path("src/plugins")
    fpath = Path(r"G:\My Drive\Banking\Import\CAPONE-AUTO_20240211_20240227.pdf")
    entry_point = "plugins.pdf.capitaloneauto:Parser"
    test_plugin_manager(plugin_dir, fpath, entry_point)
