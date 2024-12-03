import sys
import traceback
from datetime import datetime, timedelta
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
    QGroupBox,
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

from core import learn, plot, query, reports
from core.categorize import categorize_uncategorized, categorize_unverified
from core.db import create_new_db
from core.dialog import (
    AddAccount,
    CompletenessDialog,
    InsertTransaction,
    PreferencesDialog,
)
from core.statements import StatementProcessor
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

        # Maximize to primary screen
        screen = QApplication.primaryScreen()
        geometry = screen.availableGeometry()
        self.setGeometry(geometry)
        self.showMaximized()

        # MENU BAR #######################
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("File")
        file_menu.addAction("Open Database", self.open_db)
        file_menu.addAction("Preferences", self.preferences)

        # Accounts Menu
        accounts_menu = menubar.addMenu("Accounts")
        accounts_menu.addAction("Show Accounts", self.show_accounts)

        # Accounts Menu
        statements_menu = menubar.addMenu("Statements")
        statements_menu.addAction("Import All", self.import_all_statements)
        statements_menu.addAction("Pick File for Import", self.import_one_statement)
        statements_menu.addAction("Completeness Grid", self.statement_matrix)

        # Transactions Menu
        transactions_menu = menubar.addMenu("Transactions")
        transactions_menu.addAction("Insert Manually", self.insert_transaction)
        transactions_menu.addAction("Plot Balances", self.plot_balances)
        transactions_menu.addAction("Plot Categories", self.plot_categories)

        # Reports Menu
        reports_menu = menubar.addMenu("Reports")
        reports_menu.addAction("Export Three Months", self.report_3months)
        reports_menu.addAction("Export One Year", self.report_1year)
        reports_menu.addAction("Export All Time", self.report_all_time)

        # Categorize Menu
        categorize_menu = menubar.addMenu("Categorize")
        categorize_menu.addAction(
            "Uncategorized Transactions", self.categorize_uncategorized
        )
        categorize_menu.addAction("Unverified Transactions", self.categorize_unverified)
        categorize_menu.addAction(
            "Train Pipeline for Testing", self.train_pipeline_test
        )
        categorize_menu.addAction(
            "Train Pipeline for Deployment", self.train_pipeline_save
        )

        # Help Menu
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About", self.about)

        # INITIALIZE CONFIGURATION ################
        self.config_path = Path("") / "config.ini"
        self.config = read_config(self.config_path)
        self.db_path = Path(self.config.get("DATABASE", "db_path")).resolve()

        # Make sure a database exists and initialize an empty one if it doesn't
        self.ensure_db()

        ##################
        # CENTRAL WIDGET #
        ##################
        # Create the main layout and central widget
        central_widget = QWidget(self)
        self.grid_layout = QGridLayout(central_widget)
        self.setCentralWidget(central_widget)

        ### Create the latest balances table view
        self.table_view = QTableView()
        self.table_view.setSortingEnabled(True)
        self.grid_layout.addWidget(self.table_view, 0, 0, 4, 1)

        ### Create balance history control group
        balance_controls_layout = QGridLayout()

        # Add account name selection
        row = 0
        balance_account_label = QLabel("Select Accounts:")
        balance_controls_layout.addWidget(balance_account_label, row, 0, 1, 2)
        row += 1

        # Add "Select All" checkbox
        select_all_accounts_checkbox = QCheckBox("Select All")
        select_all_accounts_checkbox.setCheckState(Qt.Checked)
        balance_controls_layout.addWidget(select_all_accounts_checkbox, row, 0, 1, 2)
        row += 1

        # Add checkable accounts list for plot filtering
        self.account_select_list = QListWidget()
        balance_controls_layout.addWidget(self.account_select_list, row, 0, 1, 2)
        row += 1

        # Connect "Select All" checkbox to toggle function
        def toggle_select_all_accounts(state):
            for index in range(self.account_select_list.count()):
                item = self.account_select_list.item(index)
                item.setCheckState(Qt.Checked if state == Qt.Checked else Qt.Unchecked)

        select_all_accounts_checkbox.stateChanged.connect(toggle_select_all_accounts)

        # Add days of smoothing selection
        balance_smoothing_label = QLabel("Smoothing Days:")
        balance_controls_layout.addWidget(balance_smoothing_label, row, 0, 1, 1)
        self.balance_smoothing_input = QLineEdit("0")
        self.balance_smoothing_input.setPlaceholderText("Enter number of days")
        self.balance_smoothing_input.editingFinished.connect(
            lambda: self.validate_int(self.balance_smoothing_input, 0)
        )
        balance_controls_layout.addWidget(self.balance_smoothing_input, row, 1, 1, 1)
        row += 1

        # Add years of balance history selection
        balance_years_label = QLabel("Years of History:")
        balance_controls_layout.addWidget(balance_years_label, row, 0, 1, 1)
        self.balance_years_input = QLineEdit("10")
        self.balance_years_input.setPlaceholderText("Enter number of years")
        self.balance_years_input.editingFinished.connect(
            lambda: self.validate_float(self.balance_years_input, 10)
        )
        balance_controls_layout.addWidget(self.balance_years_input, row, 1, 1, 1)
        row += 1

        # Add Update Balance Plot button
        balance_filter_button = QPushButton("Update Balance Plot")
        balance_filter_button.clicked.connect(self.update_balance_history_chart)
        balance_controls_layout.addWidget(balance_filter_button, row, 0, 1, 2)

        # Place the QGridLayout in a GroupBox so its max size can be set
        balance_controls_group = QGroupBox("Balance History Controls")
        balance_controls_group.setLayout(balance_controls_layout)
        balance_controls_group.adjustSize()
        max_width = int(0.7 * balance_controls_group.sizeHint().width())
        balance_controls_group.setMaximumWidth(max_width)
        self.grid_layout.addWidget(
            balance_controls_group, 0, 1, 2, 1, alignment=Qt.AlignTop
        )

        ### Create Category Spending control group
        category_controls_layout = QGridLayout()

        # Add category selection
        row = 0
        select_category_label = QLabel("Select Categories:")
        category_controls_layout.addWidget(select_category_label, row, 0, 1, 2)
        row += 1

        # Add "Select All" checkbox
        select_all_category_checkbox = QCheckBox("Select All")
        select_all_category_checkbox.setCheckState(Qt.Checked)
        category_controls_layout.addWidget(select_all_category_checkbox, row, 0, 1, 2)
        row += 1

        # Add checkable accounts list for plot filtering
        self.category_select_list = QListWidget()
        category_controls_layout.addWidget(self.category_select_list, row, 0, 1, 2)
        row += 1

        # Connect "Select All" checkbox to toggle function
        def toggle_select_all_categories(state):
            for index in range(self.category_select_list.count()):
                item = self.category_select_list.item(index)
                item.setCheckState(Qt.Checked if state == Qt.Checked else Qt.Unchecked)

        select_all_category_checkbox.stateChanged.connect(toggle_select_all_categories)

        # Add days of smoothing selection
        category_smoothing_label = QLabel("Smoothing Months:")
        category_controls_layout.addWidget(category_smoothing_label, row, 0, 1, 1)
        self.category_smoothing_input = QLineEdit("0")
        self.category_smoothing_input.setPlaceholderText("Enter number of days")
        self.category_smoothing_input.editingFinished.connect(
            lambda: self.validate_int(self.category_smoothing_input, 0)
        )
        category_controls_layout.addWidget(self.category_smoothing_input, row, 1, 1, 1)
        row += 1

        # Add years of balance history selection
        category_years_label = QLabel("Years of History:")
        category_controls_layout.addWidget(category_years_label, row, 0, 1, 1)
        self.category_years_input = QLineEdit("10")
        self.category_years_input.setPlaceholderText("Enter number of years")
        self.category_years_input.editingFinished.connect(
            lambda: self.validate_float(self.category_years_input, 10)
        )
        category_controls_layout.addWidget(self.category_years_input, row, 1, 1, 1)
        row += 1

        # Add Update Balance Plot button
        category_filter_button = QPushButton("Update Category Plot")
        category_filter_button.clicked.connect(self.update_category_spending_chart)
        category_controls_layout.addWidget(category_filter_button, row, 0, 1, 2)

        # Place the QGridLayout in a GroupBox so its max size can be set
        category_controls_group = QGroupBox("Category Spending Controls")
        category_controls_group.setLayout(category_controls_layout)
        category_controls_group.adjustSize()
        max_width = int(0.7 * category_controls_group.sizeHint().width())
        category_controls_group.setMaximumWidth(max_width)
        self.grid_layout.addWidget(
            category_controls_group, 2, 1, 2, 1, alignment=Qt.AlignTop
        )

        ### Add balance history chart
        balance_canvas = MatplotlibCanvas(self, width=7, height=5)
        self.balance_ax = balance_canvas.axes
        self.grid_layout.addWidget(balance_canvas, 1, 2, 1, 1)
        balance_toolbar = NavigationToolbar(balance_canvas, self)
        self.grid_layout.addWidget(balance_toolbar, 0, 2, 1, 1)

        ### Add category spending chart
        category_canvas = MatplotlibCanvas(self, width=7, height=5)
        self.category_ax = category_canvas.axes
        self.grid_layout.addWidget(category_canvas, 3, 2, 1, 1)
        category_toolbar = NavigationToolbar(category_canvas, self)
        self.grid_layout.addWidget(category_toolbar, 2, 2, 1, 1)

        self.setCentralWidget(central_widget)

        # Initialize all tables, checklists, and graphs
        self.update_main_gui()

    def exception_hook(self, exc_type, exc_value, exc_traceback):
        """
        Handle uncaught exceptions by displaying an error dialog with traceback.
        """
        # Show the error in a message box
        tb = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Unhandled Exception")
        msg_box.setText("An unexpected error occurred:\n" + tb)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
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

    #########################
    ### MENUBAR FUNCTIONS ###
    #########################
    def open_db(self):
        open_file_in_os(self.db_path)

    def preferences(self):
        dialog = PreferencesDialog(self.config_path)
        if dialog.exec_() == QDialog.Accepted:
            self.config = read_config(self.config_path)
            self.db_path = Path(self.config.get("DATABASE", "db_path"))
            self.update_main_gui()

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
            # Update all GUI elements
            self.update_main_gui()

    def insert_transaction(self):
        dialog = InsertTransaction(self.db_path)
        if dialog.exec_() == QDialog.Accepted:
            # Update all GUI elements
            self.update_main_gui()

    def import_all_statements(self):
        # Import everything
        processor = StatementProcessor(self.config)
        processor.import_all(parent=self)

        # Update all GUI elements
        self.update_main_gui()

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
        processor = StatementProcessor(self.config)
        processor.import_one(fpath)

        # Update all GUI elements
        self.update_main_gui()

    def statement_matrix(self):
        dialog = CompletenessDialog(self.db_path)
        if dialog.exec_() == QDialog.Accepted:
            pass

    def plot_balances(self):
        plot.plot_balance_history(self.db_path)

    def plot_categories(self):
        plot.plot_category_spending(self.db_path)

    def report_all_time(self):
        report_dir = Path(self.config.get("REPORTS", "report_dir")).resolve()
        timestamp = datetime.now().strftime(r"%Y%m%d%H%M%S")
        dpath = report_dir / f"{timestamp}_Report_AllTime.xlsx"
        reports.report(self.db_path, dpath)

    def report_1year(self):
        report_dir = Path(self.config.get("REPORTS", "report_dir")).resolve()
        timestamp = datetime.now().strftime(r"%Y%m%d%H%M%S")
        dpath = report_dir / f"{timestamp}_Report_OneYear.xlsx"
        reports.report(
            self.db_path, dpath, where="WHERE Date >= DATE('now', '-1 year')"
        )

    def report_3months(self):
        report_dir = Path(self.config.get("REPORTS", "report_dir")).resolve()
        timestamp = datetime.now().strftime(r"%Y%m%d%H%M%S")
        dpath = report_dir / f"{timestamp}_Report_ThreeMonths.xlsx"
        reports.report(
            self.db_path, dpath, where="WHERE Date >= DATE('now', '-3 month')"
        )

    def train_pipeline_test(self):
        data, columns = query.training_set(self.db_path, where="WHERE Verified=1")
        if len(data) == 0:
            QMessageBox.information(
                self,
                "No Verified Categories",
                "There are no verified transactions to train a model.",
            )
            return
        df = pd.DataFrame(data, columns=columns)

        # Train and test a pipeline
        learn.train_pipeline_test(df, amount=False)

    def train_pipeline_save(self):
        # Get old model path
        model_path = self.config.get("CLASSIFIER", "model_path")
        try:
            model_path = Path(model_path).resolve()
        except:
            model_path = Path("") / "pipeline.mdl"

        # Prompt user for new save location
        options = QFileDialog.Options()
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Save Location",
            str(model_path),
            "MDL Files (*.mdl);;All Files (*);;",
            options=options,
        )
        if save_path == "":
            return
        model_path = Path(save_path).resolve()

        # Retrieve verified transactions
        data, columns = query.training_set(self.db_path, where="WHERE Verified=1")
        if len(data) == 0:
            QMessageBox.information(
                self,
                "No Verified Categories",
                "There are no verified transactions to train a model.",
            )
            return
        df = pd.DataFrame(data, columns=columns)

        # Train and save pipeline
        learn.train_pipeline_save(df, model_path, amount=False)

        QMessageBox.information(
            self, "Pipeline Saved", "Trained pipeline has been saved successfully."
        )

        # Save new pipeline path to config
        if Path("").resolve() == model_path.parents[0]:
            model_path = model_path.name
        else:
            model_path = str(model_path)
        self.config.set("CLASSIFIER", "model_path", str(model_path))
        with open("config.ini", "w") as configfile:
            self.config.write(configfile)

    def categorize_uncategorized(self):
        model_path = Path(self.config.get("CLASSIFIER", "model_path")).resolve()
        categorize_uncategorized(self.db_path, model_path)
        self.update_main_gui()

    def categorize_unverified(self):
        model_path = Path(self.config.get("CLASSIFIER", "model_path")).resolve()
        categorize_unverified(self.db_path, model_path)
        self.update_main_gui()

    ################################
    ### CENTRAL WIDGET FUNCTIONS ###
    ################################
    def update_main_gui(self):
        """Update all tables, checklists, and charts in the main GUI window"""
        self.setWindowTitle(f"PyGuiBank - {self.db_path.name}")
        self.update_balances_table()
        self.update_accounts_checklist()
        self.update_category_checklist()
        self.update_balance_history_chart()
        self.update_category_spending_chart()

    def update_accounts_checklist(self):
        account_names = [
            "Net Worth",
            "Total Assets",
            "Total Debts",
        ] + query.account_names(self.db_path)
        self.update_checklist(self.account_select_list, account_names)

    def update_category_checklist(self):
        category_names = query.distinct_categories(self.db_path)
        self.update_checklist(self.category_select_list, category_names)

    def update_checklist(self, list_widget, names):
        checked, unchecked = self.get_checked_items(list_widget)
        list_widget.clear()
        for name in names:
            item = QListWidgetItem(name)
            if name in checked:
                item.setCheckState(Qt.Checked)
            elif name in unchecked:
                item.setCheckState(Qt.Unchecked)
            else:
                # New items should be checked
                item.setCheckState(Qt.Checked)
            list_widget.addItem(item)

    def update_balances_table(self):
        # Fetch data for the table
        data, columns = query.latest_balances(self.db_path)
        df_balances = pd.DataFrame(data, columns=columns)

        # Update the table contents
        table_model = PandasModel(df_balances)
        self.table_view.setModel(table_model)
        self.table_view.resizeColumnsToContents()

        # Set default sorting
        self.table_view.sortByColumn(2, Qt.DescendingOrder)

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

    def get_checked_items(
        self, list_widget: QListWidget
    ) -> tuple[list[str], list[str]]:
        checked, unchecked = [], []
        for index in range(list_widget.count()):
            item = list_widget.item(index)
            if item.checkState() == Qt.Checked:
                checked.append(item.text())
            else:
                unchecked.append(item.text())
        return checked, unchecked

    def validate_float(self, line_edit: QLineEdit, fallback: float) -> float:
        try:
            return float(line_edit.text())
        except ValueError:
            line_edit.setText(str(fallback))
            return fallback

    def validate_int(self, line_edit: QLineEdit, fallback: int) -> int:
        try:
            # Attempt to parse the input as an integer
            value = int(float(line_edit.text()))
            line_edit.setText(str(value))
            return value
        except ValueError:
            # On failure, reset to fallback
            line_edit.setText(str(fallback))
            return fallback

    def update_balance_history_chart(self):
        QApplication.processEvents()
        # Get filter prefs
        smoothing_days = self.validate_int(self.balance_smoothing_input, 0)
        limit_years = self.validate_float(self.balance_years_input, 10)
        selected_accounts, _ = self.get_checked_items(self.account_select_list)

        # Plot all balances on the same chart
        df, debt_cols = plot.get_balance_data(self.db_path)

        # Limit the data to the specified year range
        cutoff_date = datetime.now() - timedelta(days=limit_years * 365)
        df = df[df.index >= cutoff_date]

        # Apply smoothing (rolling average)
        if smoothing_days > 1:
            df = df.rolling(window=smoothing_days, min_periods=1).mean()

        # Clear the current contents of the plot
        self.balance_ax.cla()

        # Plot only account data where the account is in the checklist
        filtered_accounts = [
            acct for acct in df.columns.values if acct in selected_accounts
        ]
        for account_name in filtered_accounts:
            linestyle = "dashed" if account_name in debt_cols else "solid"
            self.balance_ax.plot(df.index, df[account_name], linestyle=linestyle)

        # Apply plot customizations
        self.balance_ax.axhline(0, color="black", linewidth=1.5, linestyle="-")
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
        QApplication.processEvents()
        # Get filter prefs
        smoothing_months = self.validate_int(self.category_smoothing_input, 0)
        limit_years = self.validate_float(self.category_years_input, 10)
        selected_cats, _ = self.get_checked_items(self.category_select_list)

        # Get the category spending data by month
        df = plot.get_category_data(self.db_path)

        # Limit the data to the specified year range
        cutoff_date = datetime.now() - timedelta(days=limit_years * 365)
        df = df[df.index >= cutoff_date]

        # Apply smoothing (rolling average)
        if smoothing_months > 1:
            df = df.rolling(window=smoothing_months, min_periods=1).mean()

        # Clear the current contents of the plot
        self.category_ax.cla()

        # Plot only the selected categories
        filtered_cats = [cat for cat in df.columns.values if cat in selected_cats]
        for category in filtered_cats:
            self.category_ax.plot(df.index, df[category])

        # Customize plot
        self.category_ax.axhline(0, color="black", linewidth=1.5, linestyle="-")
        self.category_ax.set_title("Spending by Category")
        self.category_ax.set_xlabel("Date")
        self.category_ax.set_ylabel("Amount ($)")
        self.category_ax.grid(True)
        self.category_ax.legend(filtered_cats, loc="upper left", fontsize="xx-small")

        # Show mouse hover coordinate
        self.category_ax.fmt_xdata = lambda x: mdates.num2date(x).strftime(r"%Y-%m-%d")

        # Redraw the canvas to reflect updates
        self.category_ax.figure.canvas.draw()


if __name__ == "__main__":
    # Kick off the GUI
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("pyguibank.png"))
    window = PyGuiBank()
    window.show()
    sys.exit(app.exec_())
