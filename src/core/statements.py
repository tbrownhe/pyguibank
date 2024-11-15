# -*- coding: utf-8 -*-
import csv
import hashlib
import shutil
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path

from loguru import logger
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

from core.db import execute_sql_query, insert_into_db
from core.parse import parse
from core.utils import open_file_in_os, read_config


def p(val):
    print(val)
    exit()


def update_accounts_table(
    dialog: QDialog, accounts_table: QTableWidget, max_height_ratio=0.8
):
    accounts_table.setSortingEnabled(True)
    accounts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    accounts_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    query = (
        "SELECT AccountID, Company, Description, AccountType, NickName"
        " FROM Accounts"
        " JOIN AccountTypes ON Accounts.AccountTypeID = AccountTypes.AccountTypeID"
    )
    data, columns = execute_sql_query(dialog.db_path, query)
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
        data, _ = execute_sql_query(db_path, "SELECT AccountType FROM AccountTypes")
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
        data, _ = execute_sql_query(self.db_path, query)
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
            insert_into_db(self.db_path, "Accounts", columns, [row])
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
        data, _ = execute_sql_query(self.db_path, query)
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
            insert_into_db(
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


def write_to_csv(rows, file_):
    with open(file_, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)


def hash_file_contents(fpath: Path) -> str:
    """
    Hashes the contents of a file.
    """
    with fpath.open("rb") as f:
        contents = f.read()
    md5hash = hashlib.md5(contents).hexdigest()
    return md5hash


def standardize_fname(fpath: Path, parser: str, date_range) -> str:
    """
    Creates consistent fname
    """
    fname_date = r"%Y%m%d"
    new_fname = (
        "_".join(
            [
                parser,
                date_range[0].strftime(fname_date),
                date_range[1].strftime(fname_date),
            ]
        )
        + fpath.suffix.lower()
    )
    return new_fname


def get_statement_id(db_path: Path, md5hash: str) -> int:
    """
    Retrieves a StatementID based on the md5hash.
    """
    query = "SELECT StatementID FROM Statements WHERE MD5 = '%s'" % md5hash
    data, _ = execute_sql_query(db_path, query)
    if len(data) == 0:
        return -1
    elif len(data) == 1:
        return data[0][0]
    else:
        raise KeyError("MD5 hash %s is not unique in Statements table." % md5hash)


def get_account_id(db_path: Path, STID: int, account_num: str) -> int:
    """
    Retrieves an AccountID based on an account_num string found in a statement.
    """
    query = (
        "SELECT AccountID FROM AccountNumbers WHERE AccountNumber = '%s'" % account_num
    )
    data, _ = execute_sql_query(db_path, query)
    if len(data) == 0:
        raise KeyError("Account number not found in AccountNumbers.AccountNumber")
    return data[0][0]


def get_account_nickname(db_path: Path, account_id: int) -> str:
    """
    Retrieves an Account Nickname based on an account string found in a statement.
    """
    query = "SELECT NickName FROM Accounts WHERE AccountID = %s" % account_id
    data, _ = execute_sql_query(db_path, query)
    if len(data) == 0:
        raise ValueError("No Account with AccountID = %s" % account_id)
    else:
        return data[0][0]


def statement_already_imported(db_path: Path, fpath: Path) -> bool:
    # Check if the file has already been saved to the db
    md5hash = hash_file_contents(fpath)
    imported = get_statement_id(db_path, md5hash) != -1
    return imported


def insert_statement_metadata(
    db_path: Path,
    fpath: Path,
    STID: int,
    account_id: int,
    nick_name: str,
    date_range: list[datetime],
) -> tuple[str, int]:
    """
    Updates db with information about this statement file.
    """
    # Assemble the metadata
    md5hash = hash_file_contents(fpath)
    db_date = r"%Y-%m-%d"
    columns = [
        "StatementTypeID",
        "AccountID",
        "StartDate",
        "EndDate",
        "ImportDate",
        "Filename",
        "MD5",
    ]
    start_date = date_range[0].strftime(db_date)
    end_date = date_range[1].strftime(db_date)
    import_date = datetime.now().strftime(db_date)
    new_fname = standardize_fname(fpath, nick_name, date_range)
    metadata = (
        STID,
        account_id,
        start_date,
        end_date,
        import_date,
        new_fname,
        md5hash,
    )

    # Insert metadata into db
    insert_into_db(db_path, "Statements", columns, [metadata])

    # Get the new StatementID
    statement_id = get_statement_id(db_path, md5hash)

    return new_fname, statement_id


def prompt_account_num(db_path: Path, fpath: Path, STID: int, account_num: str) -> int:
    """
    Ask user to associate this unknown account_num with an Accounts.AccountID
    """
    account_id = None
    dialog = AssignAccountNumber(db_path, fpath, STID, account_num)
    if dialog.exec_() == QDialog.Accepted:
        account_id = dialog.get_account_id()
        return account_id
    else:
        raise ValueError("No AccountID selected.")


def get_account_info(
    db_path: Path, fpath: Path, STID: int, account_nums: list[str]
) -> tuple[dict[str, int], str]:
    """
    Makes sure all accounts in the statement have an entry in the lookup table.
    Return the nicknames of all accounts
    """
    account_ids = {}
    for account_num in account_nums:
        try:
            account_id = get_account_id(db_path, STID, account_num)
        except KeyError as err:
            print(err)
            account_id = prompt_account_num(db_path, fpath, STID, account_num)
        account_ids[account_num] = account_id
    nick_name = get_account_nickname(db_path, account_ids[account_nums[0]])
    return account_ids, nick_name


def move_to_archive(fpath: Path, archive_dir: Path, dname: str) -> None:
    """
    Move a file to the archive dir
    """
    # Create the archive directory if it doesn't exist
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Move the original file to the archive
    dpath = archive_dir / dname
    while True:
        try:
            shutil.move(fpath, dpath)
            return
        except PermissionError:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setText(
                f"The statement {fpath.name} could not be moved to archive. "
                "If it's open in another program, please close it and click OK"
            )
            msg_box.setWindowTitle("Unable to move to archive")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()


def hash_transactions(transactions: list[tuple]) -> list[tuple]:
    """
    Appends the MD5 hash of the transaction contents to the last element of each row.
    This statement is only called for transactions within one statement.
    Assume statements do not contain duplicate transactions.
    If a duplicate md5 is found, modify the description and rehash.
    Description is always the last item in the row.
    """
    md5_list = []
    hashed_transactions = []
    for row in transactions:
        md5 = hashlib.md5(str(row).encode()).hexdigest()
        while md5 in md5_list:
            logger.debug("Modifying duplicate item in statement to ensure uniqueness.")
            description = row[-1] + " D"
            row = row[:-1] + (description,)
            md5 = hashlib.md5(str(row).encode()).hexdigest()
        md5_list.append(md5)
        hashed_transactions.append(row + (md5,))
    return hashed_transactions


def insert_into_shopping(db_path: Path, transactions: list[tuple]) -> None:
    """
    Insert the transactions into the shopping db table
    """
    # Add the AccountID and StatementID to the transaction list
    columns = [
        "StatementID",
        "AccountID",
        "CardID",
        "OrderID",
        "Date",
        "Amount",
        "Description",
        "MD5",
    ]

    # Insert rows into database
    insert_into_db(db_path, "Shopping", columns, transactions, skip_duplicates=True)


def insert_into_transactions(db_path: Path, transactions: list[tuple]) -> None:
    """
    Insert the transactions into the transactions db table
    """
    # Add the AccountID and StatementID to the transaction list
    columns = [
        "StatementID",
        "AccountID",
        "Date",
        "Amount",
        "Balance",
        "Description",
        "MD5",
    ]

    # Insert rows into database
    insert_into_db(db_path, "Transactions", columns, transactions, skip_duplicates=True)


def import_single(config: ConfigParser, fpath: Path):
    """
    Parses the statement and saves the transaction data to the database.
    """
    db_path = Path(config.get("DATABASE", "db_path")).resolve()

    # Abort if this statement has already been imported to db
    if statement_already_imported(db_path, fpath):
        duplicate_dir = Path(config.get("IMPORT", "duplicate_dir")).resolve()
        dpath = duplicate_dir / fpath.name
        fpath.rename(dpath)
        logger.info("Duplicate statement moved to {d}", d=dpath)
        return

    # Get all the transactions in this file.
    STID, date_range, data = parse(db_path, fpath)

    # Ensure there are listings for this account in the AccountNumbers table
    account_ids, nick_name = get_account_info(db_path, fpath, STID, list(data.keys()))

    # Insert statement metadata into db
    main_account_id = list(account_ids.values())[0]
    new_fname, statement_id = insert_statement_metadata(
        db_path, fpath, STID, main_account_id, nick_name, date_range
    )

    # Save transaction data for each account to the db
    for account, transactions in data.items():
        if len(transactions) == 0:
            continue

        # Prepend AccountID to each transaction row
        account_id = account_ids[account]
        transactions = [(account_id,) + row for row in transactions]

        # Hash each transaction
        transactions = hash_transactions(transactions)

        # Prepend the StatementID to each transaction row
        transactions = [(statement_id,) + row for row in transactions]

        match account:
            case "amazonper":
                insert_into_shopping(db_path, transactions)
            case "amazonbus":
                insert_into_shopping(db_path, transactions)
            case _:
                insert_into_transactions(db_path, transactions)

    # Archive the file
    move_to_archive(fpath, Path(config.get("IMPORT", "success_dir")), new_fname)


def import_all() -> None:
    """
    Finds all statements in the import_dir and imports all of them.
    """
    # Get the config
    config_path = Path("") / "config.ini"
    config = read_config(config_path)

    # Get the list of files in the input_dir
    input_dir = Path(config.get("IMPORT", "import_dir")).resolve()
    extensions = [ext.strip() for ext in config.get("IMPORT", "extensions").split(",")]
    fpaths = []
    for ext in extensions:
        fpaths.extend(input_dir.glob("*." + ext))

    # Read all the files and store as individual .csv files in the csv directory.
    for fpath in sorted(fpaths):
        logger.info("Importing {f}", f=fpath.name)
        try:
            import_single(config, fpath)
        except Exception:
            logger.exception("Import failed: ")
            if config.getboolean("IMPORT", "hard_fail"):
                raise
            else:
                failed_dir = Path(config.get("IMPORT", "fail_dir")).resolve()
                dpath = failed_dir / fpath.name
                fpath.rename(dpath)
                logger.info("Failed statement moved to {d}", d=dpath)


def main() -> None:
    """
    Script executes when run as main. Imports all statements.
    """
    import_all()


if __name__ == "__main__":
    main()
