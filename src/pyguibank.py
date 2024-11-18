import sys
import traceback
from pathlib import Path

import matplotlib.dates as mdates
import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PyQt5.QtCore import QAbstractTableModel, Qt
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableView,
    QWidget,
)

from core import plot, query, reports, statements
from core.categorize import categorize_new_transactions, train_classifier
from core.db import create_new_db
from core.dialog import AddAccount, CompletenessDialog, InsertTransaction
from core.utils import open_file_in_os, read_config


class MatplotlibCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)


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

        # Create the latest balances table view
        self.table_view = QTableView()
        self.table_view.setSortingEnabled(True)
        self.grid_layout.addWidget(self.table_view, 0, 0, 4, 1)
        self.update_balances_table()

        # Create the sub-grid for balance filtering controls
        balance_controls_layout = QGridLayout()

        # Add account name selection
        balance_account_label = QLabel("Select Account(s):")
        self.balance_account_list = QListWidget()
        balance_controls_layout.addWidget(balance_account_label, 0, 0, 1, 1)

        # Add "Select All" checkbox
        select_all_checkbox = QCheckBox("Select All")
        select_all_checkbox.setCheckState(Qt.Checked)
        balance_controls_layout.addWidget(select_all_checkbox, 1, 0, 1, 1)

        # Add checkable accounts list for plot filtering
        account_names = [
            "Net Worth",
            "Total Assets",
            "Total Debts",
        ] + query.account_names(self.db_path)
        for account in account_names:
            item = QListWidgetItem(account)
            item.setCheckState(Qt.Checked)
            self.balance_account_list.addItem(item)

        balance_controls_layout.addWidget(self.balance_account_list, 2, 0, 1, 1)

        # Connect "Select All" checkbox to toggle function
        def toggle_select_all(state):
            for index in range(self.balance_account_list.count()):
                item = self.balance_account_list.item(index)
                item.setCheckState(Qt.Checked if state == Qt.Checked else Qt.Unchecked)

        select_all_checkbox.stateChanged.connect(toggle_select_all)

        # Add years of balance history selection
        balance_years_label = QLabel("Years of History:")
        self.balance_years_input = QLineEdit("10")
        balance_controls_layout.addWidget(balance_years_label, 3, 0, 1, 1)
        balance_controls_layout.addWidget(self.balance_years_input, 4, 0, 1, 1)

        # Add filter button
        balance_filter_button = QPushButton("Update Balance Plot")
        balance_filter_button.clicked.connect(self.update_balance_history_chart)
        balance_controls_layout.addWidget(balance_filter_button, 5, 0, 1, 1)

        # Place the QGridLayout in a widget so its max size can be set
        balance_controls_widget = QWidget()
        balance_controls_widget.setLayout(balance_controls_layout)
        balance_controls_widget.adjustSize()
        max_width = int(0.7 * balance_controls_widget.sizeHint().width())
        balance_controls_widget.setMaximumWidth(max_width)

        # Add balance controls layout to the grid
        self.grid_layout.addWidget(
            balance_controls_widget, 0, 1, 2, 1, alignment=Qt.AlignTop
        )

        # Add balance history chart
        balance_canvas = MatplotlibCanvas(self, width=7, height=5)
        self.balance_ax = balance_canvas.axes
        self.grid_layout.addWidget(balance_canvas, 1, 2, 1, 1)
        balance_toolbar = NavigationToolbar(balance_canvas, self)
        self.grid_layout.addWidget(balance_toolbar, 0, 2, 1, 1)
        self.update_balance_history_chart()

        # Add category spending chart
        category_canvas = MatplotlibCanvas(self, width=7, height=5)
        self.category_ax = category_canvas.axes
        self.grid_layout.addWidget(category_canvas, 3, 2, 1, 1)
        category_toolbar = NavigationToolbar(category_canvas, self)
        self.grid_layout.addWidget(category_toolbar, 2, 2, 1, 1)
        self.update_category_spending_chart()

        self.setCentralWidget(central_widget)

    def exception_hook(self, exc_type, exc_value, exc_traceback):
        """
        Handle uncaught exceptions by displaying an error dialog.
        """
        # Show the error in a message box
        tb = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Unhandled Exception")
        msg_box.setText("An unexpected error occurred:\n" + tb)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

    def ensure_db(self):
        # Ensure db file exists
        if self.db_path.exists():
            query.optimize_db(self.db_path)
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
        # Show file selection dialog
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
        success_dir = Path(self.config.get("IMPORT", "success_dir")).resolve()
        if fpath.parents[0] == success_dir:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setText(f"Cannot import statements from the SUCCESS folder.")
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
        plot.plot_balance_history(self.db_path)

    def plot_categories(self):
        plot.plot_category_spending(self.db_path)

    def make_reports(self):
        report_dir = Path(self.config.get("REPORTS", "report_dir")).resolve()
        reports.make_reports(self.db_path, report_dir)

    def update_balances_table(self):
        # Fetch data for the table
        data, columns = query.latest_balances(self.db_path)
        df_balances = pd.DataFrame(data, columns=columns)

        # Update the table contents
        table_model = PandasModel(df_balances)
        self.table_view.setModel(table_model)
        self.table_view.resizeColumnsToContents()

        # Fix the table width
        total_width = sum(
            self.table_view.columnWidth(i)
            for i in range(self.table_view.model().columnCount())
        )
        vertical_scrollbar_width = (
            self.table_view.verticalScrollBar().sizeHint().width()
        )
        table_width = total_width + vertical_scrollbar_width + 30
        self.table_view.setFixedWidth(table_width)

    def get_selected_accounts(self):
        selected_accounts = []
        for index in range(self.balance_account_list.count()):
            item = self.balance_account_list.item(index)
            if item.checkState() == Qt.Checked:
                selected_accounts.append(item.text())
        return selected_accounts

    def update_balance_history_chart(self):
        # Get
        try:
            limit_years = float(self.balance_years_input.text())
        except ValueError:
            self.balance_years_input.setText("10")
            limit_years = 10
        selected_accounts = self.get_selected_accounts()

        # Clear the current contents of the plot
        self.balance_ax.cla()

        # Plot all balances on the same chart
        df, debt_cols = plot.get_balance_data(self.db_path)
        limit_days = int(limit_years * 365)
        df = df.iloc[-limit_days:]

        filtered_accounts = [
            acct for acct in df.columns.values if acct in selected_accounts
        ]
        for account_name in filtered_accounts:
            linestyle = "dashed" if account_name in debt_cols else "solid"
            self.balance_ax.plot(df.index, df[account_name], linestyle=linestyle)

        # Apply plot customizations
        self.balance_ax.set_title("Balance History")
        self.balance_ax.set_xlabel("Date")
        self.balance_ax.set_ylabel("Balance ($)")
        self.balance_ax.grid(True)
        self.balance_ax.legend(filtered_accounts, loc="upper left", fontsize="xx-small")

        # Show mouse hover coordinate
        self.balance_ax.fmt_xdata = lambda x: mdates.num2date(x).strftime(r"%Y-%m-%d")

        # Redraw the canvas to reflect updates
        self.balance_ax.figure.canvas.draw()

    def update_category_spending_chart(self):
        # Clear the current contents of the plot
        self.category_ax.cla()

        # Plot spending by category
        df = plot.get_category_data(self.db_path)
        for category in df.columns.values:
            self.category_ax.plot(df.index, df[category])

        # Customize plot
        self.category_ax.set_title("Spending by Category")
        self.category_ax.set_xlabel("Date")
        self.category_ax.set_ylabel("Amount ($)")
        self.category_ax.grid(True)
        self.category_ax.legend(
            df.columns.values, loc="upper left", fontsize="xx-small"
        )

        # Show mouse hover coordinate
        self.category_ax.fmt_xdata = lambda x: mdates.num2date(x).strftime(r"%Y-%m-%d")

        # Rotate x-axis labels for better readability
        # for label in self.category_ax.get_xticklabels():
        #    label.set_rotation(45)

        # Redraw the canvas to reflect updates
        self.category_ax.figure.canvas.draw()


if __name__ == "__main__":
    # Kick off the GUI
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("pyguibank.png"))
    window = PyGuiBank()
    window.show()
    sys.exit(app.exec_())
