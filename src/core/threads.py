from packaging import version
from PyQt5.QtCore import QThread, pyqtSignal

from core.client import get_client_installers, is_newer_version
from core.plugins import compare_plugins, get_plugin_lists
from core.settings import settings
from gui.plugins import PluginManager


class ClientUpdateThread(QThread):
    """Checks for plugins in a separate thread"""

    # Success, latest_installer or {}
    update_available = pyqtSignal(bool, dict, str)

    def __init__(self, parent=None):
        super().__init__()

    def run(self):
        try:
            # Get the list of installers for the user's platform
            installers = get_client_installers()
            platform_installers = [i for i in installers if i["platform"] == settings.platform]

            # Return if there are no installers available
            if not platform_installers:
                self.update_available.emit(True, {}, "No Installers Available")
                return

            # Determine if the latest installer is later than the currently installed verison
            latest_installer = max(platform_installers, key=lambda i: version.parse(i["version"]))
            if is_newer_version(settings.version, latest_installer["version"]):
                self.update_available.emit(True, latest_installer, "Update Available")
            else:
                self.update_available.emit(True, {}, "Client up to date")
        except Exception as e:
            self.update_available.emit(False, {}, e)


class PluginUpdateThread(QThread):
    """Checks for plugins in a separate thread"""

    update_available = pyqtSignal(list, list)
    update_complete = pyqtSignal(bool, str)

    def __init__(self, plugin_manager: PluginManager):
        super().__init__()
        self.plugin_manager = plugin_manager

    def run(self):
        try:
            local_plugins, server_plugins = get_plugin_lists(self.plugin_manager)
            new_plugins, _ = compare_plugins(local_plugins, server_plugins)
            if new_plugins:
                self.update_available.emit(local_plugins, server_plugins)
            else:
                self.update_complete.emit(True, "")
        except Exception as e:
            self.update_complete.emit(False, f"Plugin update Failed: {e}", self.plugin_manager)
