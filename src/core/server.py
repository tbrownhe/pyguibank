import requests
from pathlib import Path
from core.plugins import PLUGIN_DIR

SERVER_URL = "http://localhost:8000/api/v1"


def get_plugins():
    """
    Fetches the list of available plugins from the server.
    """
    try:
        response = requests.get(f"{SERVER_URL}/plugins/plugins")
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
        url = f"{SERVER_URL}/plugins/plugins/{file_type}/{plugin_name}"
        with requests.get(url, stream=True) as response:
            response.raise_for_status()
            with save_path.open("wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
        print(f"Plugin {plugin_name} downloaded successfully to {save_path}")
    except requests.RequestException as e:
        print(f"Error downloading plugin {plugin_name}: {e}")


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
