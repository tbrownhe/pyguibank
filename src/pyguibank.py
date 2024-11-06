import os
import subprocess
import sys
from pathlib import Path

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget

from core.db import create_new_db
from core.missing import missing
from core.plots import plot_balances, plot_categories
from core.statements import import_all
from core.utils import read_config


# Ensure db file exists
def ensure_db():
    config = read_config(Path("") / "config.ini")
    db_path = Path(config.get("DATABASE", "db_path")).resolve()
    if not db_path.exists():
        print("No database found!")
        create_new_db(db_path)
        print(f"Created new database {db_path}")


class PyGuiBank(QMainWindow):
    def __init__(self):
        super().__init__()

        # Initialize the GUI window
        self.setWindowTitle("PyGuiBank")
        self.setGeometry(100, 100, 640, 480)

        # Create the main layout and central widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create top level menu bar
        menubar = self.menuBar()

        # Create File menu
        file_menu = menubar.addMenu("File")
        file_menu.addAction("Open", self.open_db)

        # Create buttons in the main window
        self.button_opendb = QPushButton("Open Database", self)
        self.button_statements = QPushButton("Show Statement Matrix", self)
        self.button_import = QPushButton("Import New Statements", self)
        self.button_plot_balances = QPushButton("Plot Balances", self)
        self.button_plot_categories = QPushButton("Plot Categories", self)

        layout.addWidget(self.button_opendb)
        layout.addWidget(self.button_statements)
        layout.addWidget(self.button_import)
        layout.addWidget(self.button_plot_balances)
        layout.addWidget(self.button_plot_categories)

        # Connect buttons to corresponding functions
        self.button_opendb.clicked.connect(self.open_db)
        self.button_statements.clicked.connect(missing)
        self.button_import.clicked.connect(import_all)
        self.button_plot_balances.clicked.connect(plot_balances)
        self.button_plot_categories.clicked.connect(plot_categories)

    def open_db(self):
        config = read_config(Path("") / "config.ini")
        db_path = Path(config.get("DATABASE", "db_path")).resolve()
        name = os.name
        if name == "nt":
            args = ["start", "", str(db_path)]
            subprocess.run(args, shell=True, check=True)
        elif name == "posix":
            args = ["open", str(db_path)]
            subprocess.run(args, shell=False, check=True)
        else:
            raise ValueError("Unsupported OS type %s" % name)


if __name__ == "__main__":
    # Make sure a db file exists
    ensure_db()

    # Kick off the GUI
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("pyguibank.png"))
    window = PyGuiBank()
    window.show()
    sys.exit(app.exec_())
