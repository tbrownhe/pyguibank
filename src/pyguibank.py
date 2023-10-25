# -*- coding: utf-8 -*-
import sys
import os
import subprocess
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from PyQt5.QtGui import QIcon

from core.import_statements import import_all_statements
from core.missing import missing
from core.plots import plot_balances, plot_categories


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
        file_menu.addAction("New", self.donothing)
        file_menu.addAction("Open", self.open_db)
        file_menu.addAction("Save", self.donothing)
        file_menu.addAction("Save as...", self.donothing)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)

        # Create Help menu
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("Help Index", self.donothing)
        help_menu.addAction("About...", self.donothing)

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
        self.button_import.clicked.connect(import_all_statements)
        self.button_plot_balances.clicked.connect(plot_balances)
        self.button_plot_categories.clicked.connect(plot_categories)

    def donothing(self):
        """
        Example function
        """
        pass

    def open_db(self):
        filename = Path("").resolve() / "pyguibank.db"
        name = os.name
        if name == "nt":
            args = ["start", "", str(filename)]
            subprocess.run(args, shell=True, check=True)
        elif name == "posix":
            args = ["open", str(filename)]
            subprocess.run(args, shell=False, check=True)
        else:
            raise ValueError("Unsupported OS type %s" % name)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("pig.png"))
    window = PyGuiBank()
    window.show()
    sys.exit(app.exec_())
