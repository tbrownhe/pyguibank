import os
import signal
import sys
from contextlib import suppress
from pathlib import Path
from platform import system

from dotenv import load_dotenv
from loguru import logger
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

# Load .env file if present
dotenv_path = Path(__file__).parents[1] / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path, override=True)
    logger.info(f"Loaded .env from {dotenv_path}")

# Set PyQt environment variables
os.environ.setdefault("QT_API", "PyQt5")  # Specify the Qt bindings to use
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"  # Enable HiDPI scaling for PyQt apps

# Platform-specific environment configurations
if system() == "Windows":
    # Use Windows-specific platform plugin
    os.environ["QT_QPA_PLATFORM"] = "windows"
elif system == "Darwin":
    # macOS-specific scaling (already set above for consistency)
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"


# Then load modules that may depend on env vars and settings
from gui.main_window import PyGuiBank


def handle_signal(signal, frame):
    logger.info("Application interrupted. Exiting...")
    sys.exit(0)


if __name__ == "__main__":
    # Handle system interrupts (e.g., Ctrl+C)
    signal.signal(signal.SIGINT, handle_signal)

    # Close the splash screen
    with suppress(ModuleNotFoundError):
        import pyi_splash  # type: ignore

        pyi_splash.close()

    # Kick off the GUI
    try:
        app = QApplication(sys.argv)
        app.setWindowIcon(QIcon(str(Path("assets/pyguibank_128px.ico"))))
        window = PyGuiBank()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        logger.exception("An error occurred during application execution")
        sys.exit(1)
