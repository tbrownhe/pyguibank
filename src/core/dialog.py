from pathlib import Path

import pandas as pd
from PyQt5.QtCore import QAbstractTableModel, QDate, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from . import db, query
from .missing import get_missing_coverage
from .utils import hash_transactions, open_file_in_os


def update_accounts_table(
    dialog: QDialog, accounts_table: QTableWidget, max_height_ratio=0.8
):
    accounts_table.setSortingEnabled(True)
    accounts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    accounts_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    data, columns = query.accounts(dialog.db_path)
    accounts_table.setRowCount(len(data))
    accounts_table.setColumnCount(len(columns))
    accounts_table.setHorizontalHeaderLabels(columns)
    accounts_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

    for row_idx, row_data in enumerate(data):
        for col_idx, cell_data in enumerate(row_data):
            item = QTableWidgetItem(str(cell_data))
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            accounts_table.setItem(row_idx, col_idx, item)

    # Set minimum width based on table contents
    accounts_table.resizeColumnsToContents()
    pad = 200 if len(data) == 0 else 60
    total_width = sum(
        accounts_table.columnWidth(i) for i in range(accounts_table.columnCount())
    )
    total_width += accounts_table.verticalHeader().width()
    total_width += accounts_table.frameWidth() * 2

    dialog.setMinimumWidth(total_width + pad)
    dialog.adjustSize()


class AddAccount(QDialog):
    def __init__(self, db_path: Path, company="", description="", account_type=""):
        super().__init__()
        self.setWindowTitle("Accounts")

        screen_height = QApplication.primaryScreen().availableGeometry().height()
        self.setMinimumHeight(int(screen_height * 0.6))
        self.setMaximumHeight(int(screen_height))
        self.setContentsMargins(10, 10, 10, 10)

        self.db_path = db_path
        self.account_cols = None

        # Main layout
        layout = QVBoxLayout(self)

        # Descriptive text
        desc1_text = "List of existing accounts:"
        desc1_label = QLabel(desc1_text)
        layout.addWidget(desc1_label)

        # Display Accounts table
        self.accounts_table = QTableWidget(self)
        layout.addWidget(self.accounts_table)
        update_accounts_table(self, self.accounts_table)

        # Descriptive text
        desc2_text = "To add an account, please fill out the following information:"
        desc2_label = QLabel(desc2_text)
        layout.addWidget(desc2_label)

        # Form layout for user inputs
        form_layout = QFormLayout()

        self.account_name_edit = QLineEdit(self)

        self.company_edit = QLineEdit(self)
        if company:
            self.company_edit.setText(company)

        self.description_edit = QLineEdit(self)
        if description:
            self.description_edit.setText(description)

        self.account_type_combo = QComboBox(self)
        data, _ = db.execute_sql_query(db_path, "SELECT AccountType FROM AccountTypes")
        account_type_list = [item[0] for item in data]
        self.account_type_combo.addItems(account_type_list)
        if account_type:
            index = account_type_list.index(account_type)
            self.account_type_combo.setCurrentIndex(index)

        # Tool tips
        self.account_name_edit.setPlaceholderText(
            "Enter a UNIQUE Account Name for the account"
        )
        self.company_edit.setToolTip("Company associated with this account")
        self.description_edit.setPlaceholderText(
            "Account description, e.g., Personal, Business, Student, etc"
        )
        self.account_type_combo.setToolTip("Choose the account type from the list")

        # Create form layout
        form_layout.addRow("Account Name:", self.account_name_edit)
        form_layout.addRow("Company:", self.company_edit)
        form_layout.addRow("Description:", self.description_edit)
        form_layout.addRow("Account Type:", self.account_type_combo)

        layout.addLayout(form_layout)

        # Submit button with validation
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.cancel)

        submit_button = QPushButton("Submit")
        submit_button.clicked.connect(self.submit)

        button_layout = QHBoxLayout()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(submit_button)
        layout.addLayout(button_layout)

        # Set the layout in the QDialog
        self.setLayout(layout)

    def cancel(self):
        self.reject()

    def submit(self):
        # Ensure required fields are filled
        if not all(
            [
                self.account_name_edit.text(),
                self.company_edit.text(),
                self.description_edit.text(),
            ]
        ):
            QMessageBox.warning(
                self, "Missing Information", "Please fill in all required fields."
            )
            return

        # Grab the AccountTypeID
        account_type = self.account_type_combo.currentText()
        query = (
            "SELECT AccountTypeID"
            " FROM AccountTypes"
            f" WHERE AccountType = '{account_type}'"
        )
        data, _ = query.execute_sql_query(self.db_path, query)
        account_type_id = data[0][0]

        # Insert new account into Accounts Table
        columns = ["AccountTypeID", "Company", "Description", "AccountName"]
        row = (
            account_type_id,
            self.company_edit.text(),
            self.description_edit.text(),
            self.account_name_edit.text(),
        )
        try:
            db.insert_into_db(self.db_path, "Accounts", columns, [row])
            QMessageBox.information(
                self, "Success", "New account has been added successfully."
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create account:\n{str(e)}")
            return


class AssignAccountNumber(QDialog):
    def __init__(
        self, db_path: Path, fpath: Path, STID: int, account_num: str, parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("New Account Number Found")

        screen_height = QApplication.primaryScreen().availableGeometry().height()
        max_height = int(screen_height * 0.8)
        self.setMinimumHeight(400)
        self.setMaximumHeight(max_height)
        self.setContentsMargins(10, 10, 10, 10)

        self.db_path = db_path
        self.fpath = fpath
        self.account_num = account_num
        self.account_id = None

        # Set up layout
        layout = QVBoxLayout()

        # Grab StatementType info for the new account number
        query = (
            "SELECT Company, Description, AccountType"
            " FROM StatementTypes"
            " JOIN AccountTypes"
            " ON StatementTypes.AccountTypeID = AccountTypes.AccountTypeID"
            f" WHERE StatementTypeID = {STID}"
        )
        data, _ = db.execute_sql_query(self.db_path, query)
        self.company = data[0][0]
        self.description = data[0][1]
        self.account_type = data[0][2]
        account_description = (" ".join(data[0][1:])).strip()

        # Display info to user
        desc1 = (
            f"A {self.company} {account_description} statement with an unknown "
            "account number was found.\n"
            f"New Account Number: {account_num}"
        )
        desc1_label = QLabel(desc1)
        layout.addWidget(desc1_label)

        # View statement button
        view_statement_button = QPushButton("View Statement")
        view_statement_button.clicked.connect(self.open_statement)
        layout.addWidget(view_statement_button)

        # Display info to user
        desc2 = "Which of the Accounts below does this account number belong to?"
        desc2_label = QLabel(desc2)
        layout.addWidget(desc2_label)

        # Display Accounts table
        self.accounts_table = QTableWidget(self)
        self.accounts_table.cellClicked.connect(self.handle_cell_click)
        layout.addWidget(self.accounts_table)
        update_accounts_table(self, self.accounts_table)

        # Add New Account button
        new_account_button = QPushButton("Create New Account")
        new_account_button.clicked.connect(self.new_account)

        # Add submit button
        submit_button = QPushButton("Submit")
        submit_button.clicked.connect(self.submit)

        button_layout = QHBoxLayout()
        button_layout.addWidget(new_account_button)
        button_layout.addWidget(submit_button)
        layout.addLayout(button_layout)

        # Set the layout in the QDialog
        self.setLayout(layout)

    def open_statement(self):
        open_file_in_os(self.fpath)

    def handle_cell_click(self, row, column):
        # Capture the AccountID of the clicked row
        account_id_item = self.accounts_table.item(
            row, 0
        )  # Assuming AccountID is in the first column
        if account_id_item:
            self.account_id = account_id_item.text()

    def new_account(self):
        dialog = AddAccount(
            self.db_path, self.company, self.description, self.account_type
        )
        if dialog.exec_() == QDialog.Accepted:
            update_accounts_table(self, self.accounts_table)

            # Auto-select the newly created account (assuming it's added to the last row)
            self.accounts_table.selectRow(self.accounts_table.rowCount() - 1)
            self.account_id = self.accounts_table.item(
                self.accounts_table.rowCount() - 1, 0
            ).text()

    def submit(self):
        """
        Gather all input values into the results dictionary and close the dialog.
        """
        # Close dialog and accept the current account ID selection
        if self.account_id is None:
            QMessageBox.warning(
                self,
                "No Account Selected",
                "Please select an account or create a new one.",
            )
        else:
            # Create the AccountNumber -> AccountID association in the db
            db.insert_into_db(
                self.db_path,
                "AccountNumbers",
                ["AccountID", "AccountNumber"],
                [(self.account_id, self.account_num)],
            )
            self.accept()

    def get_account_id(self):
        """
        Returns the results dictionary with user inputs after the dialog is accepted.
        """
        return self.account_id


class InsertTransaction(QDialog):
    def __init__(self, db_path: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Insert Transaction")
        self.setGeometry(100, 100, 400, 200)
        self.db_path = db_path

        # Main layout
        layout = QVBoxLayout(self)

        # Form layout for inputs
        form_layout = QFormLayout()

        # Dropdown to select account
        self.account_dropdown = QComboBox(self)
        self.account_dropdown.currentIndexChanged.connect(self.update_balance)

        # Labels for latest balance info
        self.latest_balance_value = QLineEdit("$0.00")
        self.latest_balance_value.setReadOnly(True)
        self.latest_balance_value.setStyleSheet(
            "color: gray; background-color: #f0f0f0;"
        )

        self.latest_date_value = QLineEdit("N/A")
        self.latest_date_value.setReadOnly(True)
        self.latest_date_value.setStyleSheet("color: gray; background-color: #f0f0f0;")

        # New transaction date selector
        self.date_selector = QDateEdit(self)
        self.date_selector.setCalendarPopup(True)
        self.date_selector.setDate(QDate.currentDate())
        self.date_selector.setDisplayFormat("yyyy-MM-dd")

        # Amount input
        self.amount_input = QLineEdit(self)
        self.amount_input.setPlaceholderText("Enter transaction amount")

        # Description input
        self.description_input = QLineEdit(self)
        self.description_input.setPlaceholderText("Enter transaction description")

        # Add inputs to the form layout
        form_layout.addRow("Account:", self.account_dropdown)
        form_layout.addRow("Latest Balance:", self.latest_balance_value)
        form_layout.addRow("As of Date:", self.latest_date_value)
        form_layout.addRow("Effective Date:", self.date_selector)
        form_layout.addRow("Amount:", self.amount_input)
        form_layout.addRow("Description:", self.description_input)

        layout.addLayout(form_layout)

        # Submit button
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.submit)
        layout.addWidget(self.submit_button)

        # Set the layout
        self.setLayout(layout)

        # Update the initial values
        self.load_accounts()
        self.update_balance()

    def load_accounts(self):
        """
        Load account names and IDs from the database and populate the dropdown.
        """
        try:
            data, _ = db.execute_sql_query(
                self.db_path, "SELECT AccountID, AccountName FROM Accounts"
            )
            for account_id, account_name in data:
                self.account_dropdown.addItem(
                    f"{account_name} (ID: {account_id})", account_id
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load accounts:\n{str(e)}")

    def update_balance(self):
        account_id = self.account_dropdown.currentData()
        if account_id:
            # Query the database for the most recent balance for this account
            data, _ = query.latest_balance(self.db_path, account_id)
            if data:
                # Set latest balance fields
                latest_date, latest_balance = data[0]
                self.latest_balance_value.setText(f"{latest_balance:.2f}")
                self.latest_date_value.setText(f"{latest_date}")
            else:
                # If no transactions found, assume balance is zero
                self.latest_balance_value.setText("$0.00")
        else:
            # Clear balance display if no account is selected
            self.latest_balance_value.setText("$0.00")

    def validate_input(self):
        # Get inputs
        account_id = self.account_dropdown.currentData()
        date = self.date_selector.date().toString("yyyy-MM-dd")
        amount = self.amount_input.text()
        balance = self.latest_balance_value.text()
        description = self.description_input.text()

        # Validate inputs
        if not account_id or not amount or not balance or not description:
            QMessageBox.warning(
                self, "Missing Information", "Please fill in all fields."
            )
            return

        # Ensure the amount is a valid number
        try:
            amount = float(amount)
            balance = float(balance) + amount
        except ValueError:
            QMessageBox.warning(
                self,
                "Invalid Amount",
                "Please enter a valid number for the amount.",
            )
            return

        # Traceability for manual entry
        description = "Manual Entry: " + description

        # Create MD5 hash
        transaction = [(account_id, date, amount, balance, description)]
        transaction = hash_transactions(transaction)

        return transaction

    def submit(self):
        """
        Validate inputs and insert the transaction into the database.
        """
        try:
            transaction = self.validate_input()

            if transaction is None:
                return

            # Insert transaction into the database
            db.insert_into_db(
                self.db_path,
                "Transactions",
                ["AccountID", "Date", "Amount", "Balance", "Description", "MD5"],
                transaction,
            )

            QMessageBox.information(
                self, "Success", "Transaction has been added successfully."
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to insert transaction:\n{str(e)}"
            )


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
        elif role == Qt.BackgroundRole:
            if value == "True":
                return QColor(140, 225, 140)  # Light green
            elif value == "False":
                return QColor(225, 160, 160)  # Light red
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignCenter  # Center-align the text
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._data.columns[section]
            if orientation == Qt.Vertical:
                return self._data.index[section]
        return None


class CompletenessDialog(QDialog):
    def __init__(self, db_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Statement Completeness Grid")

        # Main layout
        layout = QVBoxLayout()

        # Fetch DataFrame from the function
        self.df = get_missing_coverage(db_path).astype(str)

        # Create a PandasModel and attach it to a QTableView
        self.table_model = PandasModel(self.df)
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)

        # Ensure columns resize to fit contents
        self.table_view.resizeColumnsToContents()

        # Calculate the total width required for the table
        self.adjust_table_size()

        # Add the table view to the layout
        layout.addWidget(self.table_view)

        # Add a Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self.setLayout(layout)

    def adjust_table_size(self):
        """
        Adjust the size of the dialog and fix the table width based on its contents.
        """
        # Calculate the total width of the table
        total_column_width = sum(
            self.table_view.columnWidth(col)
            for col in range(self.table_model.columnCount())
        )
        vertical_scrollbar_width = (
            self.table_view.verticalScrollBar().sizeHint().width()
        )
        table_width = total_column_width + vertical_scrollbar_width + 100

        # Calculate the total height of the table
        total_row_height = sum(
            self.table_view.rowHeight(row) for row in range(self.table_model.rowCount())
        )
        horizontal_header_height = self.table_view.horizontalHeader().height()
        horizontal_scrollbar_height = (
            self.table_view.horizontalScrollBar().sizeHint().height()
        )
        table_height = (
            total_row_height
            + horizontal_header_height
            + horizontal_scrollbar_height
            + 50
        )

        # Get the available screen size
        screen = QApplication.primaryScreen().availableGeometry()
        max_width = int(screen.width() * 0.9)  # 90% of screen width
        max_height = int(screen.height() * 0.9)  # 90% of screen height

        # Constrain the dialog size to the screen size
        final_width = min(table_width, max_width)
        final_height = min(table_height, max_height)

        # Fix the table's width
        self.table_view.setMaximumWidth(final_width)
        self.table_view.setMinimumWidth(final_width)

        # Fix the layout width (optional)
        self.setFixedWidth(final_width)

        # Resize the dialog
        self.resize(final_width, final_height)
