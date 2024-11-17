import sys
import traceback
from pathlib import Path

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core import plot, reports, statements
from core.categorize import categorize_new_transactions, train_classifier
from core.db import create_new_db
from core.dialog import AddAccount, CompletenessDialog, InsertTransaction
from core.utils import open_file_in_os, read_config


class PyGuiBank(QMainWindow):
    def __init__(self):
        super().__init__()
        # Set the custom exception hook
        sys.excepthook = self.exception_hook

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

        # Accounts Menu
        statements_menu = menubar.addMenu("Statements")
        statements_menu.addAction("Import All", self.import_all_statements)
        statements_menu.addAction("Pick File for Import", self.import_one_statement)
        statements_menu.addAction("Show Matrix", self.statement_matrix)

        # Accounts Menu
        transactions_menu = menubar.addMenu("Transactions")
        transactions_menu.addAction("Insert Manually", self.insert_transaction)

        # Help Menu
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About", self.about)

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

        self.setCentralWidget(central_widget)

        # Read the configuration
        self.config = read_config(Path("") / "config.ini")
        self.db_path = Path(self.config.get("DATABASE", "db_path")).resolve()

        # Make sure a db file is ready to go
        self.ensure_db()

    def exception_hook(self, exc_type, exc_value, exc_traceback):
        """
        Handle uncaught exceptions by displaying an error dialog.
        """
        # Format the traceback
        tb = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

        # Show the error in a message box
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Unhandled Exception")
        msg_box.setText("An unexpected error occurred:\n" + tb)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

    def ensure_db(self):
        # Ensure db file exists
        if self.db_path.exists():
            return
        create_new_db(self.db_path)
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("New Database Created")
        msg_box.setText(f"Initialized new database at {self.db_path}")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

    def open_db(self):
        open_file_in_os(self.db_path)

    def about(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setText("Copyright Tobias Brown-Heft, 2024")
        msg_box.setWindowTitle("About")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

    def show_accounts(self):
        dialog = AddAccount(self.db_path)
        if dialog.exec_() == QDialog.Accepted:
            print("New account was added")

    def insert_transaction(self):
        dialog = InsertTransaction(self.db_path)
        if dialog.exec_() == QDialog.Accepted:
            print("New transaction was added")

    def import_all_statements(self):
        statements.import_all(self.config)
        import_dir = Path(self.config.get("IMPORT", "import_dir")).resolve()
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setText(f"Imported all files in {import_dir}")
        msg_box.setWindowTitle("Import Complete")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

    def import_one_statement(self):
        default_folder = self.config.get("IMPORT", "import_dir")
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_filter = "Supported Files (*.csv *.pdf *.xlsx);;All Files (*)"
        fpath, _ = QFileDialog.getOpenFileName(
            None, "Select a File", default_folder, file_filter, options=options
        )

        # Prevent weird things from happening
        if not fpath:
            return
        fpath = Path(fpath).resolve()
        if fpath.parents[0] == Path(self.config.get("IMPORT", "success_dir")).resolve():
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setText(f"Cannot import statements from the SUCCESS folder")
            msg_box.setWindowTitle("Protected Folder")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()
            return

        # Import statement
        statements.import_one(self.config, fpath)

    def statement_matrix(self):
        dialog = CompletenessDialog(self.db_path)
        if dialog.exec_() == QDialog.Accepted:
            print("Dialog Closed")

    def plot_balances(self):
        plot.balances(self.db_path)

    def plot_categories(self):
        plot.categories(self.db_path)

    def make_reports(self):
        report_dir = Path(self.config.get("REPORTS", "report_dir")).resolve()
        reports.make_reports(self.db_path, report_dir)


if __name__ == "__main__":
    # Kick off the GUI
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("pyguibank.png"))
    window = PyGuiBank()
    window.show()
    sys.exit(app.exec_())
