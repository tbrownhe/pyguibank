import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from core.initialize import initialize_db
from core.plugins import PluginManager
from core.settings import settings
from gui.plugins import ParseTestDialog

# Manually set the plugin dir to the local plugin build dir
setattr(settings, "plugin_dir", Path("dist/plugins"))

# Initialze db and plugin manager
Session = initialize_db()
plugin_manager = PluginManager()
plugin_manager.load_plugins()
for plugin_id in plugin_manager.metadata:
    print(plugin_id)

# Start the application
app = QApplication(sys.argv)
window = ParseTestDialog(Session, plugin_manager)
window.show()
sys.exit(app.exec_())
