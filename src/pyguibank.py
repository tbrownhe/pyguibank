import sys
from pathlib import Path

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core import plots, reports
from core.categorize import categorize_new_transactions, train_classifier
from core.db import create_new_db
from core.missing import missing
from core.statements import AddAccount, import_all
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

        # Create menu bar
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("File")
        file_menu.addAction("Open Database", self.open_db)

        # Accounts Menu
        accounts_menu = menubar.addMenu("Accounts")
        accounts_menu.addAction("Show Accounts", self.show_accounts)

        # Help Menu
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About", self.about)

        self.import_statements_button = QPushButton("Import New Statements", self)
        self.import_statements_button.clicked.connect(import_all)
        layout.addWidget(self.import_statements_button)

        self.statement_matrix_button = QPushButton("Show Statement Matrix", self)
        self.statement_matrix_button.clicked.connect(missing)
        layout.addWidget(self.statement_matrix_button)

        self.plot_balances_button = QPushButton("Plot Balances", self)
        self.plot_balances_button.clicked.connect(self.plot_balances)
        layout.addWidget(self.plot_balances_button)

        self.plot_categories_button = QPushButton("Plot Categories", self)
        self.plot_categories_button.clicked.connect(self.plot_categories)
        layout.addWidget(self.plot_categories_button)

        self.make_reports_button = QPushButton("Make Reports", self)
        self.make_reports_button.clicked.connect(self.make_reports)
        layout.addWidget(self.make_reports_button)

        self.button_categorize = QPushButton("Categorize New Transactions", self)
        self.button_categorize.clicked.connect(categorize_new_transactions)
        layout.addWidget(self.button_categorize)

        self.button_train = QPushButton("Retrain Classifier Model", self)
        layout.addWidget(self.button_train)
        self.button_train.clicked.connect(train_classifier)

        self.config = read_config(Path("") / "config.ini")
        self.db_path = Path(self.config.get("DATABASE", "db_path")).resolve()

    def open_db(self):
        open_file_in_os(self.db_path)

    def about(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setText(f"Copyright Tobias Brown-Heft, 2024")
        msg_box.setWindowTitle("About")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

    def show_accounts(self):
        dialog = AddAccount(self.db_path)
        if dialog.exec_() == QDialog.Accepted:
            print("New account was added")

    def plot_balances(self):
        plots.balances(self.db_path)

    def plot_categories(self):
        plots.categories(self.db_path)

    def make_reports(self):
        report_dir = Path(self.config.get("REPORTS", "report_dir")).resolve()
        reports.make_reports(self.db_path, report_dir)


if __name__ == "__main__":
    # Make sure a db file exists
    ensure_db()

    # Kick off the GUI
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("pyguibank.png"))
    window = PyGuiBank()
    window.show()
    sys.exit(app.exec_())
