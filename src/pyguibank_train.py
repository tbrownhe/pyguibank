# -*- coding: utf-8 -*-
import sys
import subprocess
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.categorize import categorize_new_transactions, train_classifier


class PyGuiBank(QMainWindow):
    def __init__(self):
        super().__init__()

        # Initialize the GUI window
        self.setWindowTitle("PyGuiBank Train")
        self.setGeometry(100, 100, 640, 480)

        # Create the main layout and central widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create buttons in the main window
        self.button_opendb = QPushButton("Open Database", self)
        self.button_categorize = QPushButton("Categorize New Transactions", self)
        self.button_train = QPushButton("Retrain Classifier Model", self)

        layout.addWidget(self.button_opendb)
        layout.addWidget(self.button_categorize)
        layout.addWidget(self.button_train)

        # Connect buttons to corresponding functions
        self.button_opendb.clicked.connect(self.open_db)
        self.button_categorize.clicked.connect(categorize_new_transactions)
        self.button_train.clicked.connect(train_classifier)

    def open_db(self):
        filename = str(Path("") / "pyguibank.db")
        subprocess.run(["open", filename], check=True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PyGuiBank()
    window.show()
    sys.exit(app.exec_())
