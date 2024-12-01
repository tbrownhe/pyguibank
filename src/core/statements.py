import shutil
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path

from loguru import logger
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QMessageBox, QProgressDialog

from . import query
from .db import insert_into_db
from .dialog import AssignAccountNumber
from .parse import parse
from .utils import hash_file, hash_transactions
from .validation import Statement


def move_file_safely(fpath: Path, dpath: Path):
    # Make sure destination parent dir exists
    dpath.parents[0].mkdir(parents=True, exist_ok=True)

    while True:
        try:
            shutil.move(fpath, dpath)
            return
        except PermissionError:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setText(
                f"The statement {fpath.name} could not be moved."
                " If it's open in another program, please close it and click OK"
            )
            msg_box.setWindowTitle("Unable to Move File")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()


def standardize_dpath(statement: Statement, success_dir: Path) -> Statement:
    """
    Creates consistent destination path.
    Uses first account as the main account.
    """
    dname = (
        "_".join(
            [
                statement.accounts[0].account_name,
                statement.start_date.strftime(r"%Y-%m-%d"),
                statement.end_date.strftime(r"%Y-%m-%d"),
            ]
        )
        + statement.fpath.suffix.lower()
    )
    statement.dpath = success_dir / dname
    return statement


def insert_statement_metadata(db_path: Path, statement: Statement) -> Statement:
    """
    Updates db with information about this statement file.
    """
    for account in statement.accounts:
        # Assemble the metadata
        columns = [
            "StatementTypeID",
            "AccountID",
            "ImportDate",
            "StartDate",
            "EndDate",
            "StartBalance",
            "EndBalance",
            "TransactionCount",
            "Filename",
            "MD5",
        ]
        metadata = (
            statement.stid,
            account.account_id,
            datetime.now().strftime(r"%Y-%m-%d"),
            statement.start_date.strftime(r"%Y-%m-%d"),
            statement.end_date.strftime(r"%Y-%m-%d"),
            account.start_balance,
            account.end_balance,
            len(account.transactions),
            statement.dpath.name,
            statement.md5hash,
        )

        # Insert metadata into db
        insert_into_db(db_path, "Statements", columns, [metadata])

        # Get the new StatementID
        account.statement_id = query.statement_id(
            db_path, account.account_id, statement.md5hash
        )

    return statement


def insert_statement_data(db_path: Path, statement: Statement) -> None:
    # Save transaction data for each account to the db
    for account in statement.accounts:
        if len(account.transactions) == 0:
            # Skip. There will still be metadata in Statements table
            continue

        # Construct list of tuple containing transaction data
        transactions = []
        for transaction in account.transactions:
            transactions.append(
                (
                    account.account_id,
                    transaction.posting_date,
                    transaction.amount,
                    transaction.balance,
                    transaction.desc,
                )
            )

        # Hash each transaction
        transactions = hash_transactions(transactions)

        # Prepend the StatementID to each transaction row
        transactions = [(account.statement_id,) + row for row in transactions]

        match account.account_name:
            case "amazonper":
                insert_into_shopping(db_path, transactions)
            case "amazonbus":
                insert_into_shopping(db_path, transactions)
            case _:
                insert_into_transactions(db_path, transactions)


def insert_into_shopping(db_path: Path, transactions: list[tuple]) -> None:
    """
    Insert the transactions into the shopping db table
    """
    # Insert rows into database
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
    insert_into_db(db_path, "Shopping", columns, transactions, skip_duplicates=True)


def insert_into_transactions(db_path: Path, transactions: list[tuple]) -> None:
    """
    Insert the transactions into the transactions db table
    """
    # Insert rows into database
    columns = [
        "StatementID",
        "AccountID",
        "Date",
        "Amount",
        "Balance",
        "Description",
        "MD5",
    ]
    insert_into_db(db_path, "Transactions", columns, transactions, skip_duplicates=True)


def file_already_imported(db_path: Path, md5hash: str) -> bool:
    """Check if the file has already been saved to the db

    Args:
        db_path (Path): Path to db
        md5hash (str): Byte hash of passed file

    Returns:
        bool: Whether md56hash exists in the db already
    """
    data = query.statements_containing_hash(db_path, md5hash)
    if len(data) == 0:
        return False

    for statement_id, filename in data:
        logger.info(
            f"Previously imported {filename} (StatementID: {statement_id})"
            f" has identical hash {md5hash}"
        )
    return True


def statement_already_imported(db_path: Path, filename: Path) -> bool:
    """Check if the file has already been saved to the db

    Args:
        db_path (Path): Path to db
        filename (str): Name of statement file after standardization

    Returns:
        bool: Whether md56hash exists in the db already
    """
    data = query.statements_containing_filename(db_path, filename)
    if len(data) == 0:
        return False

    for statement_id, filename in data:
        logger.info(f"Previously imported {filename} (StatementID: {statement_id})")
    return True


def prompt_account_num(db_path: Path, fpath: Path, stid: int, account_num: str) -> int:
    """
    Ask user to associate this unknown account_num with an Accounts.AccountID
    """
    dialog = AssignAccountNumber(db_path, fpath, stid, account_num)
    if dialog.exec_() == QDialog.Accepted:
        return dialog.get_account_id()
    raise ValueError("No AccountID selected.")


def get_account_info(db_path: Path, statement: Statement) -> Statement:
    """
    Makes sure all accounts in the statement have an entry in the lookup table.
    Return the nicknames of all accounts
    """
    # Ensure an account-to-account_num association is set up for each account_num
    for account in statement.accounts:
        try:
            # Lookup existing account
            account.account_id = query.account_id(db_path, account.account_num)
        except KeyError:
            # Prompt user to select account to associate with this account_num
            account.account_id = prompt_account_num(
                db_path, statement.fpath, statement.stid, account.account_num
            )

        # Get the account_name for this account_id
        account.account_name = query.account_name(db_path, account.account_id)

    return statement


def import_one(config: ConfigParser, fpath: Path):
    """
    Parses the statement and saves the transaction data to the database.
    """
    logger.info("Importing {f}", f=fpath.name)
    db_path = Path(config.get("DATABASE", "db_path")).resolve()
    success_dir = Path(config.get("IMPORT", "success_dir")).resolve()

    # Abort if this exact statement file has already been imported to db
    md5hash = hash_file(fpath)
    if file_already_imported(db_path, md5hash):
        duplicate_dir = Path(config.get("IMPORT", "duplicate_dir")).resolve()
        dpath = duplicate_dir / fpath.name
        move_file_safely(fpath, dpath)
        logger.info("Duplicate statement moved to {d}", d=dpath)
        return 0, 1

    # Extract the statement data into a Statement dataclass
    statement = parse(db_path, fpath)
    statement.md5hash = md5hash

    # Ensure there are listings for this account in the AccountNumbers table
    statement = get_account_info(db_path, statement)

    # Create a destination path based on the statement metadata
    statement = standardize_dpath(statement, success_dir)

    # Abort if a statement with similar metadata has been imported
    if statement_already_imported(db_path, statement.dpath.name):
        duplicate_dir = Path(config.get("IMPORT", "duplicate_dir")).resolve()
        dpath = duplicate_dir / fpath.name
        move_file_safely(fpath, dpath)
        logger.info("Duplicate statement moved to {d}", d=dpath)
        return 0, 1

    # Insert statement metadata into db
    statement = insert_statement_metadata(db_path, statement)

    # Insert transactions into db
    insert_statement_data(db_path, statement)

    # Rename and move the statement file to the success directory
    move_file_safely(statement.fpath, statement.dpath)
    return 1, 0


def import_all(config: ConfigParser, parent=None):
    """
    Finds all statements in the import_dir and imports all of them.
    """
    # Get the list of files in the input_dir
    import_dir = Path(config.get("IMPORT", "import_dir")).resolve()
    extensions = [ext.strip() for ext in config.get("IMPORT", "extensions").split(",")]
    fpaths = []
    for ext in extensions:
        fpaths.extend(import_dir.glob("*." + ext))

    # Create progress dialog
    progress = QProgressDialog(
        "Importing statements...", "Cancel", 0, len(fpaths), parent
    )
    progress.setWindowTitle("Import Progress")
    progress.setWindowModality(Qt.WindowModal)
    progress.setValue(0)

    # Import all files
    success = 0
    duplicate = 0
    fail = 0
    for idx, fpath in enumerate(sorted(fpaths)):
        if progress.wasCanceled():
            QMessageBox.information(
                parent, "Import Canceled", "The import was canceled."
            )
            break
        try:
            suc, dup = import_one(config, fpath)
            success += suc
            duplicate += dup
        except Exception:
            fail += 1
            logger.exception("Import failed: ")
            if config.getboolean("IMPORT", "hard_fail"):
                raise
            else:
                failed_dir = Path(config.get("IMPORT", "fail_dir")).resolve()
                dpath = failed_dir / fpath.name
                try:
                    shutil.move(fpath, dpath)
                    logger.info("Failed statement moved to {d}", d=dpath)
                except PermissionError:
                    logger.exception("Move to FAIL folder failed: ")

        # Update progress dialog
        progress.setValue(idx + 1)

    return len(fpaths), success, duplicate, fail
