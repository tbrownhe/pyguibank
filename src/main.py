import os
import signal
import sys
from contextlib import suppress

from loguru import logger
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

from core.init import initialize_plugins
from core.utils import resource_path
from gui.main_window import PyGuiBank

# Set environment variables
# Specify the Qt bindings to use
os.environ.setdefault("QT_API", "PyQt5")
# Enable HiDPI scaling for PyQt apps
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

# Platform-specific environment configurations
if sys.platform == "win32":
    # Use Windows-specific platform plugin
    os.environ["QT_QPA_PLATFORM"] = "windows"
elif sys.platform == "darwin":
    # macOS-specific scaling (already set above for consistency)
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

# Copy any bundled plugins to the user's plugin folder if it doesn't exist yet
initialize_plugins()


def handle_signal(signal, frame):
    logger.info("Application interrupted. Exiting...")
    sys.exit(0)


if __name__ == "__main__":
    # Handle system interrupts (e.g., Ctrl+C)
    signal.signal(signal.SIGINT, handle_signal)

    # Close the splash screen
    with suppress(ModuleNotFoundError):
        import pyi_splash  # type: ignore

        pyi_splash.update_text("Loading PyGuiBank...")
        pyi_splash.close()

    # Kick off the GUI
    try:
        app = QApplication(sys.argv)
        app.setWindowIcon(QIcon(str(resource_path("assets/pyguibank.png"))))
        window = PyGuiBank()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        logger.exception("An error occurred during application execution")
        sys.exit(1)
