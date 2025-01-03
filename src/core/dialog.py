import math
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from PyQt5.QtCore import QAbstractTableModel, QDate, Qt
from PyQt5.QtGui import QColor, QIntValidator
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session, sessionmaker

from . import cluster, query
from .orm import AccountNumbers, Accounts, Transactions
from .utils import open_file_in_os, read_config
from .validation import Statement, Transaction, ValidationError


class PreferencesDialog(QDialog):
    def __init__(self, config_path: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.resize(500, 400)

        self.config = read_config(config_path)

        # Main layout
        main_layout = QVBoxLayout(self)

        # Create grid layout for form fields
        grid_layout = QGridLayout()
        main_layout.addLayout(grid_layout)

        row = 0
        # DATABASE section
        grid_layout.addWidget(QLabel("Database Path:"), row, 0)
        self.db_path_edit = QLineEdit(self.config.get("DATABASE", "db_path"))
        grid_layout.addWidget(self.db_path_edit, row, 1)
        db_path_button = QPushButton("Select...")
        db_path_button.clicked.connect(self.select_db_path)
        grid_layout.addWidget(db_path_button, row, 2)
        row += 1

        # CLASSIFIER section
        grid_layout.addWidget(QLabel("Classifier Path:"), row, 0)
        self.model_path_edit = QLineEdit(self.config.get("CLASSIFIER", "model_path"))
        grid_layout.addWidget(self.model_path_edit, row, 1)
        model_path_button = QPushButton("Select...")
        model_path_button.clicked.connect(self.select_mdl_path)
        grid_layout.addWidget(model_path_button, row, 2)
        row += 1

        # IMPORT section
        grid_layout.addWidget(QLabel("Import Extensions:"), row, 0)
        self.extensions_edit = QLineEdit(self.config.get("IMPORT", "extensions"))
        grid_layout.addWidget(self.extensions_edit, row, 1)
        row += 1

        grid_layout.addWidget(QLabel("Import Directory:"), row, 0)
        self.import_dir_edit = QLineEdit(self.config.get("IMPORT", "import_dir"))
        grid_layout.addWidget(self.import_dir_edit, row, 1)
        import_dir_button = QPushButton("Select...")
        import_dir_button.clicked.connect(
            lambda: self.select_folder(self.import_dir_edit)
        )
        grid_layout.addWidget(import_dir_button, row, 2)
        row += 1

        grid_layout.addWidget(QLabel("Success Directory:"), row, 0)
        self.success_dir_edit = QLineEdit(self.config.get("IMPORT", "success_dir"))
        grid_layout.addWidget(self.success_dir_edit, row, 1)
        success_dir_button = QPushButton("Select...")
        success_dir_button.clicked.connect(
            lambda: self.select_folder(self.success_dir_edit)
        )
        grid_layout.addWidget(success_dir_button, row, 2)
        row += 1

        grid_layout.addWidget(QLabel("Fail Directory:"), row, 0)
        self.fail_dir_edit = QLineEdit(self.config.get("IMPORT", "fail_dir"))
        grid_layout.addWidget(self.fail_dir_edit, row, 1)
        fail_dir_button = QPushButton("Select...")
        fail_dir_button.clicked.connect(lambda: self.select_folder(self.fail_dir_edit))
        grid_layout.addWidget(fail_dir_button, row, 2)
        row += 1

        grid_layout.addWidget(QLabel("Duplicate Directory:"), row, 0)
        self.duplicate_dir_edit = QLineEdit(self.config.get("IMPORT", "duplicate_dir"))
        grid_layout.addWidget(self.duplicate_dir_edit, row, 1)
        duplicate_dir_button = QPushButton("Select...")
        duplicate_dir_button.clicked.connect(
            lambda: self.select_folder(self.duplicate_dir_edit)
        )
        grid_layout.addWidget(duplicate_dir_button, row, 2)
        row += 1

        grid_layout.addWidget(QLabel("Hard Fail:"), row, 0)
        self.hard_fail_checkbox = QCheckBox()
        self.hard_fail_checkbox.setChecked(
            self.config.getboolean("IMPORT", "hard_fail")
        )
        grid_layout.addWidget(self.hard_fail_checkbox, row, 1)
        row += 1

        # REPORTS section
        grid_layout.addWidget(QLabel("Report Directory:"), row, 0)
        self.report_dir_edit = QLineEdit(self.config.get("REPORTS", "report_dir"))
        grid_layout.addWidget(self.report_dir_edit, row, 1)
        report_dir_button = QPushButton("Select...")
        report_dir_button.clicked.connect(
            lambda: self.select_folder(self.report_dir_edit)
        )
        grid_layout.addWidget(report_dir_button, row, 2)
        row += 1

        # Buttons
        button_layout = QVBoxLayout()
        main_layout.addLayout(button_layout)

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_preferences)
        button_layout.addWidget(save_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

    def select_db_path(self):
        self.select_path(self.db_path_edit, "Database Files (*.db)")

    def select_mdl_path(self):
        self.select_path(self.model_path_edit, "Model Files (*.mdl)")

    def select_path(self, line_edit, ftype: str):
        """Select a path"""
        try:
            default_path = str(Path(line_edit.text()).resolve())
        except:
            default_path = ""
        fpath, _ = QFileDialog.getOpenFileName(
            self,
            "Select File",
            default_path,
            f"{ftype};;All Files (*)",
        )
        if fpath:
            fpath = Path(fpath).resolve()
            if fpath.parents[0] == Path("").resolve():
                line_edit.setText(fpath.name)
            else:
                line_edit.setText(str(fpath))

    def select_folder(self, line_edit):
        """Select a folder and set its path in the specified QLineEdit."""
        try:
            default_path = str(Path(line_edit.text()).resolve())
        except:
            default_path = ""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder", default_path
        )
        if folder_path:
            folder_path = Path(folder_path).resolve()
            line_edit.setText(str(folder_path))

    def save_preferences(self):
        """Save the preferences to the configuration file."""
        self.config.set("DATABASE", "db_path", self.db_path_edit.text())
        self.config.set("CLASSIFIER", "model_path", self.model_path_edit.text())
        self.config.set("IMPORT", "extensions", self.extensions_edit.text())
        self.config.set("IMPORT", "import_dir", self.import_dir_edit.text())
        self.config.set("IMPORT", "success_dir", self.success_dir_edit.text())
        self.config.set("IMPORT", "fail_dir", self.fail_dir_edit.text())
        self.config.set("IMPORT", "duplicate_dir", self.duplicate_dir_edit.text())
        self.config.set("IMPORT", "hard_fail", str(self.hard_fail_checkbox.isChecked()))
        self.config.set("REPORTS", "report_dir", self.report_dir_edit.text())

        with open("config.ini", "w") as configfile:
            self.config.write(configfile)

        QMessageBox.information(
            self, "Preferences Saved", "Preferences have been saved successfully."
        )
        self.accept()


def update_accounts_table(
    dialog: QDialog,
    session: Session,
    accounts_table: QTableWidget,
):
    accounts_table.setSortingEnabled(True)
    accounts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    accounts_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    data, columns = query.accounts_details(session)
    accounts_table.setRowCount(len(data))
    accounts_table.setColumnCount(len(columns))
    accounts_table.setHorizontalHeaderLabels(columns)
    accounts_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

    appreciation_idx = len(columns) - 1
    for row_idx, row_data in enumerate(data):
        for col_idx, value in enumerate(row_data):
            if col_idx == appreciation_idx:
                value = f"{value:.4f}" if value != 0 else "0"
            item = QTableWidgetItem(str(value))
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


class EditAccounts(QDialog):
    def __init__(
        self, Session: sessionmaker, company="", description="", account_type=""
    ):
        super().__init__()
        self.setWindowTitle("Edit Accounts")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        screen_height = QApplication.primaryScreen().availableGeometry().height()
        self.setMinimumHeight(int(screen_height * 0.6))
        self.setMaximumHeight(int(screen_height))
        self.setContentsMargins(10, 10, 10, 10)

        self.Session = Session
        self.selected_account = None

        # Main layout
        layout = QVBoxLayout(self)

        # Descriptive text
        desc1_text = "List of existing accounts:"
        desc1_label = QLabel(desc1_text)
        layout.addWidget(desc1_label)

        # Display Accounts table
        self.accounts_table = QTableWidget(self)
        layout.addWidget(self.accounts_table)
        with self.Session() as session:
            update_accounts_table(self, session, self.accounts_table)
        self.accounts_table.cellClicked.connect(self.populate_fields)

        # Descriptive text
        desc2_text = (
            "To add or edit an account, please fill out the following information:"
        )
        desc2_label = QLabel(desc2_text)
        layout.addWidget(desc2_label)

        # Form layout for user inputs
        form_layout = QFormLayout()

        self.account_name_edit = QLineEdit(self)
        self.company_edit = QLineEdit(self)
        self.description_edit = QLineEdit(self)
        self.account_type_combo = QComboBox(self)

        with self.Session() as session:
            account_types = query.account_types(session)
        self.account_type_combo.addItems(account_types)

        self.appreciation_edit = QLineEdit(self)
        self.appreciation_edit.setPlaceholderText("Enter annual appreciation rate (%)")
        self.appreciation_edit.setEnabled(False)

        self.account_type_combo.currentTextChanged.connect(
            self.toggle_appreciation_field
        )

        form_layout.addRow("Account Name:", self.account_name_edit)
        form_layout.addRow("Company:", self.company_edit)
        form_layout.addRow("Description:", self.description_edit)
        form_layout.addRow("Account Type:", self.account_type_combo)
        form_layout.addRow("Appreciation Rate (%):", self.appreciation_edit)

        layout.addLayout(form_layout)

        # Action buttons
        button_layout = QHBoxLayout()
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        self.add_button = QPushButton("Add Account")
        self.add_button.setStyleSheet("background-color: lightgreen; color: black;")
        self.add_button.clicked.connect(self.add_account)
        button_layout.addWidget(self.add_button)

        self.edit_button = QPushButton("Edit Account")
        self.edit_button.setStyleSheet("background-color: lightblue; color: black;")
        self.edit_button.clicked.connect(self.edit_account)
        self.edit_button.setEnabled(False)  # Disabled by default
        button_layout.addWidget(self.edit_button)

        self.delete_button = QPushButton("Delete Account")
        self.delete_button.setStyleSheet("background-color: lightcoral; color: black;")
        self.delete_button.clicked.connect(self.delete_account)
        self.delete_button.setEnabled(False)  # Disabled by default
        button_layout.addWidget(self.delete_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def toggle_appreciation_field(self, account_type: str):
        """
        Enable or disable the Appreciation Rate field based on account type.
        """
        if account_type == "TangibleAsset":
            self.appreciation_edit.setEnabled(True)
        else:
            self.appreciation_edit.clear()
            self.appreciation_edit.setEnabled(False)

    def populate_fields(self, row: int, column: int):
        """
        Populate fields with the data from the selected account in the table.
        """
        self.selected_account = self.accounts_table.item(row, 0).text()
        self.account_name_edit.setText(self.selected_account)
        self.company_edit.setText(self.accounts_table.item(row, 1).text())
        self.description_edit.setText(self.accounts_table.item(row, 2).text())
        self.account_type_combo.setCurrentText(self.accounts_table.item(row, 3).text())
        if self.appreciation_edit.isEnabled():
            self.appreciation_edit.setText(self.accounts_table.item(row, 4).text())
        self.edit_button.setEnabled(True)
        self.delete_button.setEnabled(True)

    def add_account(self):
        """
        Add a new account.
        """
        if not self.validate_fields():
            return

        account_type = self.account_type_combo.currentText()
        with self.Session() as session:
            account_type_id = query.account_type_id(session, account_type)

        appreciation_rate = self.get_appreciation_rate()

        row = {
            "AccountTypeID": account_type_id,
            "Company": self.company_edit.text(),
            "Description": self.description_edit.text(),
            "AccountName": self.account_name_edit.text(),
            "AppreciationRate": appreciation_rate or 0.0,
        }

        try:
            with self.Session() as session:
                query.insert_rows_batched(session, Accounts, [row])
            QMessageBox.information(self, "Success", "Account added successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add account:\n{str(e)}")
        self.refresh_table()

    def edit_account(self):
        """
        Edit the selected account.
        """
        confirm = QMessageBox.question(
            self,
            "Edit Account",
            f"Are you sure you want to edit the account '{self.selected_account}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        if not self.validate_fields():
            return

        account_type = self.account_type_combo.currentText()
        appreciation_rate = self.get_appreciation_rate()

        try:
            with self.Session() as session:
                account_type_id = query.account_type_id(session, account_type)
                query.update_account_details(
                    session,
                    account_name=self.selected_account,
                    account_type_id=account_type_id,
                    company=self.company_edit.text(),
                    desc=self.description_edit.text(),
                    appreciation=appreciation_rate or 0.0,
                )
            QMessageBox.information(self, "Success", "Account updated successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update account:\n{str(e)}")
        self.refresh_table()

    def delete_account(self):
        """
        Delete the selected account.
        """
        confirm = QMessageBox.question(
            self,
            "Delete Account",
            f"Are you sure you want to delete the account '{self.selected_account}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            with self.Session() as session:
                session.query(Accounts).filter_by(
                    AccountName=self.selected_account
                ).delete()
                session.commit()
            QMessageBox.information(self, "Success", "Account deleted successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete account:\n{str(e)}")
        self.refresh_table()

    def validate_fields(self) -> bool:
        """
        Validate required fields.
        """
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
            return False
        return True

    def get_appreciation_rate(self) -> float:
        """
        Get the appreciation rate value.
        """
        if self.appreciation_edit.isEnabled():
            try:
                return float(self.appreciation_edit.text())
            except ValueError:
                QMessageBox.warning(
                    self,
                    "Invalid Input",
                    "Please enter a valid number for appreciation rate.",
                )
                return None
        return 0.0

    def refresh_table(self):
        """
        Refresh the accounts table.
        """
        with self.Session() as session:
            update_accounts_table(self, session, self.accounts_table)
        self.clear_fields()

    def clear_fields(self):
        """
        Clear the input fields.
        """
        self.account_name_edit.clear()
        self.company_edit.clear()
        self.description_edit.clear()
        self.account_type_combo.setCurrentIndex(0)
        self.appreciation_edit.clear()
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)


class AssignAccountNumber(QDialog):
    def __init__(
        self,
        Session: sessionmaker,
        fpath: Path,
        stid: int,
        account_num: str,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("New Account Number Found")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        screen_height = QApplication.primaryScreen().availableGeometry().height()
        self.setMinimumHeight(int(screen_height * 0.6))
        self.setMaximumHeight(int(screen_height))
        self.setContentsMargins(10, 10, 10, 10)

        self.Session = Session
        self.fpath = fpath
        self.account_num = account_num
        self.account_id = None

        # Set up layout
        layout = QVBoxLayout()

        # Grab StatementType info for the new account number
        with self.Session() as session:
            result = query.statement_type_details(session, stid)
            self.company, self.description, self.account_type = result
            account_description = " ".join(
                [self.description, self.account_type]
            ).strip()

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
            update_accounts_table(self, session, self.accounts_table)

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
            self.account_id = int(account_id_item.text())

    def new_account(self):
        dialog = EditAccounts(
            self.Session, self.company, self.description, self.account_type
        )
        if dialog.exec_() == QDialog.Accepted:
            with self.Session() as session:
                update_accounts_table(self, session, self.accounts_table)

            # Auto-select the newly created account (assuming it's added to the last row)
            self.accounts_table.selectRow(self.accounts_table.rowCount() - 1)
            self.account_id = int(
                self.accounts_table.item(self.accounts_table.rowCount() - 1, 0).text()
            )

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
            row = {
                "AccountID": self.account_id,
                "AccountNumber": self.account_num,
            }
            with self.Session() as session:
                query.insert_rows_batched(session, AccountNumbers, [row])

            self.accept()

    def get_account_id(self):
        """
        Returns the results dictionary with user inputs after the dialog is accepted.
        """
        return self.account_id


class InsertTransaction(QDialog):
    def __init__(
        self, Session: sessionmaker, account_name="", close_account=False, parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("Insert Transaction")
        self.setGeometry(100, 100, 400, 200)
        self.Session = Session
        self.account_name = account_name
        self.close_account = close_account

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
            with self.Session() as session:
                data = query.accounts_with_ids(session)

            selected_index = -1
            for index, (account_id, account_name) in enumerate(data):
                self.account_dropdown.addItem(
                    f"{account_name} (ID: {account_id})", account_id
                )
                if self.account_name and account_name == self.account_name:
                    selected_index = index

            # Set the dropdown to the selected index if a match was found
            if selected_index != -1:
                self.account_dropdown.setCurrentIndex(selected_index)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load accounts:\n{str(e)}")

    def update_balance(self):
        QApplication.processEvents()
        account_id = self.account_dropdown.currentData()
        if account_id:
            # Query the database for the most recent balance for this account
            with self.Session() as session:
                result = query.latest_balance(session, account_id)
            if result:
                # Set latest balance fields
                latest_date, latest_balance = result
                self.latest_balance_value.setText(f"{latest_balance:.2f}")
                self.latest_date_value.setText(f"{latest_date}")

                # Handle account closure shortcut
                if self.close_account:
                    close_date = datetime.strptime(
                        latest_date, r"%Y-%m-%d"
                    ) + timedelta(days=30)
                    self.date_selector.setDate(
                        QDate(close_date.year, close_date.month, close_date.day)
                    )
                    self.amount_input.setText(f"{-latest_balance:.2f}")
                    self.description_input.setText("Account Closed Manually")

            else:
                # If no transactions found, assume balance is zero
                self.latest_balance_value.setText("0.00")
                self.latest_date_value.setText("N/A")
        else:
            # Clear balance display if no account is selected
            self.latest_balance_value.setText("0.00")
            self.latest_date_value.setText("N/A")

    def validate_input(self) -> tuple[int, list[Transaction]]:
        # Get inputs
        account_id = self.account_dropdown.currentData()
        q_date = self.date_selector.date()
        date = datetime(q_date.year(), q_date.month(), q_date.day())
        amount = self.amount_input.text()
        balance = self.latest_balance_value.text()
        desc = self.description_input.text()

        # Validate inputs
        if not account_id or not amount or not balance or not desc:
            QMessageBox.warning(
                self, "Missing Information", "Please fill in all fields."
            )
            return

        # Ensure the amount is a valid number
        try:
            amount = float(amount)
            balance = round(float(balance) + amount, 2)
        except ValueError:
            QMessageBox.warning(
                self,
                "Invalid Amount",
                "Please enter a valid number for the amount.",
            )
            return

        # Traceability for manual entry
        desc = "Manual Entry: " + desc

        # Create transaction object
        transactions = [
            Transaction(
                transaction_date=date,
                posting_date=date,
                amount=amount,
                desc=desc,
                balance=balance,
            )
        ]

        return account_id, transactions

    def insert_transaction(self):
        account_id, transactions = self.validate_input()

        # Hash transaction
        transactions = Transaction.hash_transactions(account_id, transactions)

        # Validate transactions before insertion
        errors = Transaction.validate_complete(transactions)
        if errors:
            raise ValidationError("\n".join(errors))

            # Convert to list of dict for db insertion
        statement_id = None
        rows = Transaction.to_db_rows(statement_id, account_id, transactions)

        # Insert transaction into the database
        with self.Session() as session:
            query.insert_rows_carefully(
                session,
                Transactions,
                rows,
                skip_duplicates=True,
            )
            session.commit()

    def submit(self):
        """
        Validate inputs and insert the transaction into the database.
        """
        try:
            self.insert_transaction()

            QMessageBox.information(
                self, "Success", "Transaction has been added successfully."
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to insert transaction:\n{str(e)}"
            )


def get_missing_coverage(Session: sessionmaker, months=12):
    """
    Returns a DataFrame showing coverage for the first of the month for each account.
    """
    with Session() as session:
        data, columns = query.statement_date_ranges(session, months=months + 3)
    df = pd.DataFrame(data, columns=columns)
    df["StartDate"] = pd.to_datetime(df["StartDate"])
    df["EndDate"] = pd.to_datetime(df["EndDate"])

    start_date = df["StartDate"].min() - timedelta(weeks=4)
    end_date = df["EndDate"].max() + timedelta(weeks=4)
    date_range = pd.date_range(start_date, end_date, freq="D")
    nick_names = df["AccountName"].unique()
    df_missing = pd.DataFrame("Missing", index=date_range, columns=nick_names)

    # Set all days that have statement coverage to True
    for i in range(len(df)):
        account = df["AccountName"].iloc[i]
        start_date = df["StartDate"].iloc[i]
        end_date = df["EndDate"].iloc[i]
        df_missing.loc[start_date:end_date, account] = "OK"

    # Stack the table so coverage is all in a single column
    df_stacked = (
        df_missing.stack()
        .reset_index()
        .rename(columns={"level_0": "Date", "level_1": "AccountName", 0: "Coverage"})
    )

    # Add a month column
    df_stacked["Month"] = df_stacked["Date"].dt.strftime(r"%Y-%m-01")

    # Make a pivot table showing coverage for the first of the month
    df_pivot = df_stacked.pivot_table(
        values="Coverage", index="Month", columns="AccountName", aggfunc="first"
    )

    # Return the last 13 months as a transposed DataFrame
    return df_pivot.tail(months).T.astype(str)


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
            if value == "OK":
                return QColor(140, 225, 140)  # Light green
            elif value == "Missing":
                return QColor(225, 160, 160)  # Light red
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._data.columns[section]
            if orientation == Qt.Vertical:
                return self._data.index[section]
        return None


class CompletenessDialog(QDialog):
    def __init__(self, Session: sessionmaker, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Statement Completeness Grid")

        # Main layout
        layout = QVBoxLayout()

        # Fetch DataFrame from the function
        self.df = get_missing_coverage(Session, months=60)

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
        max_width = int(screen.width() * 0.95)
        max_height = int(screen.height() * 0.95)

        # Constrain the dialog size to the screen size
        final_width = min(table_width, max_width)
        final_height = min(table_height, max_height)

        # Fix the table's width
        self.table_view.setMaximumWidth(final_width)

        # Resize the dialog
        self.resize(final_width, final_height)


class ValidationErrorDialog(QDialog):
    def __init__(self, statement: Statement, errors: str, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Validation Error")
        self.resize(600, 400)

        layout = QVBoxLayout(self)

        # Text display for errors
        error_display = QTextEdit(self)
        error_display.setReadOnly(True)

        # Generate the full display text
        statement_data = self.format_statement(statement)
        display_text = f"Errors:\n{errors}\n\n{statement_data}"
        error_display.setPlainText(display_text)
        layout.addWidget(error_display)

        # Close button
        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

    def format_statement(self, statement) -> str:
        """
        Format the Statement data for display, handling up to three levels:
        Statement > Account > Transaction.
        """
        if not is_dataclass(statement):
            raise ValueError("Expected a dataclass instance.")

        output = []

        # Format the top-level Statement fields
        output.append("Statement Data:")
        for field, value in asdict(statement).items():
            if field == "accounts":
                output.append("  accounts:")
                for account in value:
                    output.append(self.format_account(account, level=2))
            else:
                output.append(f"  {field}: {value}")

        return "\n".join(output)

    def format_account(self, account, level=2) -> str:
        """
        Format an Account dataclass, including nested Transactions.
        """
        indent = "  " * level
        output = []

        # Format Account fields
        output.append(f"{indent}Account:")
        for field, value in account.items():
            if field == "transactions":
                output.append(f"{indent}  transactions:")
                for transaction in value:
                    output.append(self.format_transaction(transaction, level + 2))
            else:
                output.append(f"{indent}  {field}: {value}")

        return "\n".join(output)

    def format_transaction(self, transaction, level=3) -> str:
        """
        Format a Transaction dataclass.
        """
        indent = "  " * level
        output = []

        # Format Transaction fields
        output.append(f"{indent}Transaction:")
        for field, value in transaction.items():
            output.append(f"{indent}  {field}: {value}")

        return "\n".join(output)


class BalanceCheckDialog(QDialog):
    def __init__(self, account_name: str, balance: float, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Account Balance Alert")
        self.setMinimumWidth(400)

        # Main layout
        layout = QVBoxLayout()

        # Informational message
        neg = "-" if balance < 0 else ""
        balance = abs(round(balance, 2))
        message = (
            f"The account '{account_name}' has a non-zero balance of {neg}${balance} "
            "and no recent transactions.\n\n"
            "Would you like to bring the account to zero by inserting a transaction manually?"
        )
        label = QLabel(message)
        label.setWordWrap(True)
        layout.addWidget(label)

        # Buttons
        button_layout = QHBoxLayout()
        self.yes_button = QPushButton("Yes")
        self.no_button = QPushButton("No")
        button_layout.addWidget(self.yes_button)
        button_layout.addWidget(self.no_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Connect buttons to dialog result
        self.yes_button.clicked.connect(self.accept)
        self.no_button.clicked.connect(self.reject)


class TransactionTableModel(QAbstractTableModel):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self._data = data  # Expecting a pandas DataFrame
        self.headers = list(data.columns)

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self.headers)

    def data(self, index, role):
        if not index.isValid():
            return None

        value = self._data.iloc[index.row(), index.column()]

        if role == Qt.DisplayRole:
            return str(value)  # Display as a string
        if role == Qt.TextAlignmentRole:
            return Qt.AlignRight if isinstance(value, (int, float)) else Qt.AlignLeft

        return None

    def headerData(self, section, orientation, role):
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Horizontal:
            return self.headers[section]  # Column headers
        elif orientation == Qt.Vertical:
            return str(section + 1)  # Row numbers

    def sort(self, column, order):
        """Sort the table by the given column."""
        col_name = self.headers[column]
        ascending = order == Qt.AscendingOrder
        self.layoutAboutToBeChanged.emit()
        self._data.sort_values(by=col_name, ascending=ascending, inplace=True)
        self.layoutChanged.emit()

    def update_data(self, new_data: pd.DataFrame):
        """Update the model with new data."""
        self.layoutAboutToBeChanged.emit()
        self._data = new_data
        self.headers = list(new_data.columns)
        self.layoutChanged.emit()


class RecurringTransactionsDialog(QDialog):
    def __init__(self, Session: sessionmaker, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recurring Transactions Analysis")

        # Fit primary screen
        screen = QApplication.primaryScreen()
        geometry = screen.availableGeometry()
        self.resize(int(0.6 * geometry.width()), int(0.8 * geometry.height()))

        self.Session = Session
        self.clustered = None
        self.columns = [
            "AccountName",
            "Date",
            "Amount",
            "Category",
            "Cluster",
            "Description",
        ]

        # Main layout
        main_layout = QVBoxLayout(self)

        # Control section layout
        control_widget = QWidget()
        control_layout = QGridLayout()
        control_widget.setLayout(control_layout)

        # Start date and end date selectors
        row = 0
        start_date_label = QLabel("Start Date:")
        start_date_label.setAlignment(Qt.AlignRight)
        control_layout.addWidget(start_date_label, row, 0)
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addYears(-1))
        control_layout.addWidget(self.start_date, row, 1)

        end_date_label = QLabel("Start Date:")
        end_date_label.setAlignment(Qt.AlignRight)
        control_layout.addWidget(end_date_label, row, 2)

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        control_layout.addWidget(self.end_date, row, 3)
        row += 1

        # Clustering options
        self.include_amount_checkbox = QCheckBox(
            "Include Amount in Clustering Analysis"
        )
        control_layout.addWidget(self.include_amount_checkbox, row, 2, 1, 2)
        row += 1

        # Sliders
        self.eps_slider = self._create_slider(
            "Cluster Separation (Epsilon)", 1, 200, 50, 100
        )
        self.min_samples_slider = self._create_slider(
            "Min Members per Cluster", 1, 10, 2, 1
        )
        self.min_frequency_slider = self._create_slider(
            "Min Interval (days)", 1, 30, 3, 1
        )
        self.max_interval_slider = self._create_slider(
            "Max Interval (days)", 1, 100, 35, 1, show_inf=True
        )
        self.variance_slider = self._create_slider(
            "Max Amount Variance (%)", 0, 300, 100, 1, show_inf=True
        )

        sliders = [
            self.eps_slider,
            self.min_samples_slider,
            self.min_frequency_slider,
            self.max_interval_slider,
            self.variance_slider,
        ]
        for row, slider in enumerate(sliders, start=row):
            control_layout.addWidget(slider["label"], row, 0, 1, 2)
            control_layout.addWidget(slider["slider"], row, 2, 1, 2)
        row += 1

        # Analyze button
        analyze_button = QPushButton("Analyze")
        analyze_button.clicked.connect(self.analyze_transactions)
        control_layout.addWidget(analyze_button, row, 2, 1, 2)

        # Add the control section to the main layout
        main_layout.addWidget(control_widget)

        # Table for displaying results
        self.table = QTableView()
        self.model = TransactionTableModel(pd.DataFrame([], columns=self.columns))
        self.table.setModel(self.model)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        main_layout.addWidget(self.table)

        # Save Table and Close buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save Table")
        self.save_button.clicked.connect(self.save_to_csv)
        button_layout.addWidget(self.save_button)

        self.close_button = QPushButton("Close", self)
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)

        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def _create_slider(
        self, label, min_val, max_val, default_val, divide_by, show_inf=False
    ):
        precision = int(math.ceil(math.log10(divide_by)))
        slider_label = QLabel(f"{label}: {default_val / divide_by:.{precision}f}")
        slider_label.setAlignment(Qt.AlignRight)
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default_val)

        def update_label(value):
            if show_inf and value == max_val:
                slider_label.setText(f"{label}: Inf")
            else:
                slider_label.setText(f"{label}: {value / divide_by:.{precision}f}")

        slider.valueChanged.connect(update_label)
        return {"slider": slider, "label": slider_label}

    def inf_slider(self, slider):
        value = 1e6 if slider.value() == slider.maximum() else slider.value()
        return value

    def analyze_transactions(self):
        # Retrieve and process transactions
        start_date = self.start_date.date().toPyDate()
        end_date = self.end_date.date().toPyDate()

        with self.Session() as session:
            data, columns = query.transactions_in_range(session, start_date, end_date)
        transactions = pd.DataFrame(data, columns=columns)

        if transactions.empty:
            self.table.setRowCount(0)
            return

        # Preprocess and cluster
        eps = self.eps_slider["slider"].value() / 100
        min_samples = self.min_samples_slider["slider"].value()
        min_frequency = self.min_frequency_slider["slider"].value()
        max_interval = self.inf_slider(self.max_interval_slider["slider"])
        max_variance = self.inf_slider(self.variance_slider["slider"])
        include_amount = self.include_amount_checkbox.isChecked()

        # Perform the clustering
        self.clustered = cluster.recurring_transactions(
            transactions,
            eps=eps,
            min_samples=min_samples,
            min_frequency=min_frequency,
            max_interval=max_interval,
            include_amount=include_amount,
            max_variance=max_variance,
        )

        # Update table
        self.model.update_data(self.clustered[self.columns].reset_index(drop=True))

    def update_table(self, df: pd.DataFrame):
        self.table.setRowCount(len(df))
        for row_index, row in df.iterrows():
            self.table.setItem(row_index, 0, QTableWidgetItem(row["AccountName"]))
            self.table.setItem(
                row_index, 1, QTableWidgetItem(row["Date"].strftime("%Y-%m-%d"))
            )
            self.table.setItem(row_index, 2, QTableWidgetItem(f"${row['Amount']:.2f}"))
            self.table.setItem(row_index, 3, QTableWidgetItem(str(row["Cluster"])))
            self.table.setItem(row_index, 4, QTableWidgetItem(row["Description"]))

        # Sort by Cluster
        self.table.sortItems(3, Qt.AscendingOrder)

    def save_to_csv(self):
        """
        Save the clustered transactions to a CSV file.
        """
        if self.clustered is None:
            QMessageBox.warning(
                self, "No Data", "There are no clustered transactions to save."
            )
            return

        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Clustered Transactions",
            "",
            "CSV Files (*.csv);;All Files (*)",
            options=options,
        )
        if file_path:
            try:
                # Save the dataframe to CSV
                self.clustered.to_csv(file_path, index=False)
                QMessageBox.information(
                    self, "Success", f"Clustered transactions saved to {file_path}."
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {e}")


class AppreciationCalculator(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Appreciation Rate Calculator")
        self.resize(400, 250)

        # Main layout
        layout = QVBoxLayout(self)

        # Descriptive text
        desc_text = (
            "This calculator estimates the Appreciation Rate of a Tangible Asset.\n"
            "The result can be used for Tangible Assets entered manually into\n"
            "the Edit Accounts Dialog."
        )
        desc_label = QLabel(desc_text)
        layout.addWidget(desc_label)

        # Form layout for user inputs
        form_layout = QFormLayout()

        # Start date selector
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addYears(-1))  # Default: 1 year ago
        form_layout.addRow("Start Date:", self.start_date)

        # End date selector
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())  # Default: today
        form_layout.addRow("End Date:", self.end_date)

        # Starting value input
        self.start_value_edit = QLineEdit()
        self.start_value_edit.setPlaceholderText("Enter the starting value")
        form_layout.addRow("Starting Value:", self.start_value_edit)

        # Ending value input
        self.end_value_edit = QLineEdit()
        self.end_value_edit.setPlaceholderText("Enter the ending value")
        form_layout.addRow("Ending Value:", self.end_value_edit)

        # Output display
        self.result_edit = QLineEdit()
        self.result_edit.setReadOnly(True)
        self.result_edit.setPlaceholderText("Annual Appreciation Rate (%)")
        form_layout.addRow("Appreciation Rate (%)", self.result_edit)

        layout.addLayout(form_layout)

        # Button layout
        button_layout = QHBoxLayout()

        # Submit button
        self.submit_button = QPushButton("Calculate")
        self.submit_button.clicked.connect(self.calculate_appreciation_rate)
        button_layout.addWidget(self.submit_button)

        # Close button
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

    def calculate_appreciation_rate(self):
        try:
            # Extract input values
            start_date = self.start_date.date().toPyDate()
            end_date = self.end_date.date().toPyDate()
            start_value = float(self.start_value_edit.text())
            end_value = float(self.end_value_edit.text())

            # Validate inputs
            if start_date >= end_date:
                raise ValueError("Start Date must be earlier than End Date.")
            if start_value <= 0 or end_value <= 0:
                raise ValueError("Values must be positive.")

            # Calculate appreciation rate
            days = (end_date - start_date).days
            annual_rate = (
                (end_value / start_value) ** (365 / days) - 1
            ) * 100  # Convert to percentage

            # Display result
            self.result_edit.setText(f"{annual_rate:.2f}")
        except ValueError as e:
            QMessageBox.warning(self, "Input Error", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")
