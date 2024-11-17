import sys
import traceback
from pathlib import Path

import pandas as pd
from PyQt5.QtCore import QAbstractTableModel, Qt
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QGridLayout,
    QMainWindow,
    QMessageBox,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core import plot, reports, statements
from core.categorize import categorize_new_transactions, train_classifier
from core.db import create_new_db
from core.dialog import AddAccount, CompletenessDialog, InsertTransaction
from core.query import latest_balances, optimize_db
from core.utils import open_file_in_os, read_config


class PandasModel(QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        value = self._data.iloc[index.row(), index.column()]

        if role == Qt.DisplayRole:
            return str(value)
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignCenter  # Center-align text in cells
        elif role == Qt.BackgroundRole:
            # Apply background color based on positive/negative value
            try:
                numeric_value = float(value)
                if numeric_value > 0:
                    return QColor(140, 225, 140)  # Light green
                elif numeric_value < 0:
                    return QColor(225, 160, 160)  # Light red
            except ValueError:
                return None
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._data.columns[section]
            if orientation == Qt.Vertical:
                return self._data.index[section]
        return None

    def sort(self, column, order):
        """
        Sort the model by the given column.
        :param column: The column index to sort by.
        :param order: Qt.AscendingOrder or Qt.DescendingOrder
        """
        column_name = self._data.columns[column]
        ascending = order == Qt.AscendingOrder
        self.layoutAboutToBeChanged.emit()
        self._data.sort_values(by=column_name, ascending=ascending, inplace=True)
        self._data.reset_index(drop=True, inplace=True)
        self.layoutChanged.emit()


class PyGuiBank(QMainWindow):
    def __init__(self):
        super().__init__()
        # Set the custom exception hook
        sys.excepthook = self.exception_hook

        # Initialize the GUI window
        self.setWindowTitle("PyGuiBank")
        self.resize(1000, 800)

        # MENU BAR #######################
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

        # Reports Menu
        reports_menu = menubar.addMenu("Reports")
        reports_menu.addAction("Export Excel", self.make_reports)

        # Transactions Menu
        transactions_menu = menubar.addMenu("Transactions")
        transactions_menu.addAction("Insert Manually", self.insert_transaction)
        transactions_menu.addAction("Plot Balances", self.plot_balances)
        transactions_menu.addAction("Plot Categories", self.plot_categories)

        # Categorize Menu
        categorize_menu = menubar.addMenu("Categorize")
        categorize_menu.addAction(
            "Categorize New Transactions", categorize_new_transactions
        )
        categorize_menu.addAction("Retrain Classifier Model", train_classifier)

        # Help Menu
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About", self.about)

        # INITIALIZE DATA ################

        # Read the configuration
        self.config = read_config(Path("") / "config.ini")
        self.db_path = Path(self.config.get("DATABASE", "db_path")).resolve()
        self.ensure_db()

        # CENTRAL WIDGET #################
        # Create the main layout and central widget
        central_widget = QWidget(self)
        self.grid_layout = QGridLayout(central_widget)
        self.setCentralWidget(central_widget)

        # Create the table view
        self.table_view = QTableView()
        self.table_view.setSortingEnabled(True)
        self.update_balances_table()

        # Add the table to the grid layout
        self.grid_layout.addWidget(self.table_view, 0, 0)

        self.setCentralWidget(central_widget)

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
            optimize_db(self.db_path)
        else:
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

    def update_balances_table(self):
        # Fetch data for the table
        data, columns = latest_balances(self.db_path)
        df_balances = pd.DataFrame(data, columns=columns)

        # Update the table contents
        table_model = PandasModel(df_balances)
        self.table_view.setModel(table_model)
        self.table_view.resizeColumnsToContents()


if __name__ == "__main__":
    # Kick off the GUI
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("pyguibank.png"))
    window = PyGuiBank()
    window.show()
    sys.exit(app.exec_())
