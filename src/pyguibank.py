import sys
from pathlib import Path

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget

from core.categorize import categorize_new_transactions, train_classifier
from core.db import create_new_db
from core.missing import missing
from core.plots import plot_balances, plot_categories
from core.reports import make_reports
from core.statements import import_all
from core.utils import open_file_in_os, read_config


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
        self.open_db_button = QPushButton("Open Database", self)
        self.open_db_button.clicked.connect(self.open_db)
        layout.addWidget(self.open_db_button)

        self.statement_matrix_button = QPushButton("Show Statement Matrix", self)
        self.statement_matrix_button.clicked.connect(missing)
        layout.addWidget(self.statement_matrix_button)

        self.import_statements_button = QPushButton("Import New Statements", self)
        self.import_statements_button.clicked.connect(import_all)
        layout.addWidget(self.import_statements_button)

        self.plot_balances_button = QPushButton("Plot Balances", self)
        self.plot_balances_button.clicked.connect(plot_balances)
        layout.addWidget(self.plot_balances_button)

        self.plot_categories_button = QPushButton("Plot Categories", self)
        self.plot_categories_button.clicked.connect(plot_categories)
        layout.addWidget(self.plot_categories_button)

        self.make_reports_button = QPushButton("Make Reports", self)
        self.make_reports_button.clicked.connect(make_reports)
        layout.addWidget(self.make_reports_button)

        self.button_categorize = QPushButton("Categorize New Transactions", self)
        self.button_categorize.clicked.connect(categorize_new_transactions)
        layout.addWidget(self.button_categorize)

        self.button_train = QPushButton("Retrain Classifier Model", self)
        layout.addWidget(self.button_train)
        self.button_train.clicked.connect(train_classifier)

    def open_db(self):
        config = read_config(Path("") / "config.ini")
        db_path = Path(config.get("DATABASE", "db_path")).resolve()
        open_file_in_os(db_path)


if __name__ == "__main__":
    # Make sure a db file exists
    ensure_db()

    # Kick off the GUI
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("pyguibank.png"))
    window = PyGuiBank()
    window.show()
    sys.exit(app.exec_())
