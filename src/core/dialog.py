from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from . import db, query
from .utils import open_file_in_os


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

        self.nickname_edit = QLineEdit(self)

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
        self.nickname_edit.setPlaceholderText("Enter a UNIQUE nickname for the account")
        self.company_edit.setToolTip("Company associated with this account")
        self.description_edit.setPlaceholderText(
            "Account description, e.g., Personal, Business, Student, etc"
        )
        self.account_type_combo.setToolTip("Choose the account type from the list")

        # Create form layout
        form_layout.addRow("Company:", self.company_edit)
        form_layout.addRow("Description:", self.description_edit)
        form_layout.addRow("Account Type:", self.account_type_combo)
        form_layout.addRow("Nickname:", self.nickname_edit)

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
                self.nickname_edit.text(),
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
        columns = ["AccountTypeID", "Company", "Description", "NickName"]
        row = (
            account_type_id,
            self.company_edit.text(),
            self.description_edit.text(),
            self.nickname_edit.text(),
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
