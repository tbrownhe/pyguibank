import hashlib
import shutil
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path

from loguru import logger
from PyQt5.QtWidgets import QDialog, QMessageBox

from . import query
from .db import insert_into_db
from .dialog import AssignAccountNumber
from .parse import parse
from .utils import hash_file, hash_transactions, read_config, standardize_fname


def statement_already_imported(db_path: Path, fpath: Path) -> bool:
    # Check if the file has already been saved to the db
    md5hash = hash_file(fpath)
    imported = query.statement_id(db_path, md5hash) != -1
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
    md5hash = hash_file(fpath)
    columns = [
        "StatementTypeID",
        "AccountID",
        "StartDate",
        "EndDate",
        "ImportDate",
        "Filename",
        "MD5",
    ]
    start_date = date_range[0].strftime(r"%Y-%m-%d")
    end_date = date_range[1].strftime(r"%Y-%m-%d")
    import_date = datetime.now().strftime(r"%Y-%m-%d")
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
    statement_id = query.statement_id(db_path, md5hash)

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
            account_id = query.account_id(db_path, account_num)
        except KeyError:
            account_id = prompt_account_num(db_path, fpath, STID, account_num)
        account_ids[account_num] = account_id
    nick_name = query.account_nickname(db_path, account_ids[account_nums[0]])
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
                f"The statement {fpath.name} could not be moved to archive."
                " If it's open in another program, please close it and click OK"
            )
            msg_box.setWindowTitle("Unable to move file to archive")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()


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


def import_one(config: ConfigParser, fpath: Path):
    """
    Parses the statement and saves the transaction data to the database.
    """
    logger.info("Importing {f}", f=fpath.name)
    db_path = Path(config.get("DATABASE", "db_path")).resolve()

    # Abort if this statement has already been imported to db
    if statement_already_imported(db_path, fpath):
        duplicate_dir = Path(config.get("IMPORT", "duplicate_dir")).resolve()
        dpath = duplicate_dir / fpath.name
        shutil.move(fpath, dpath)
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
        transactions = hash_transactions(account_id, transactions)

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


def import_all(config: ConfigParser) -> None:
    """
    Finds all statements in the import_dir and imports all of them.
    """
    # Get the list of files in the input_dir
    input_dir = Path(config.get("IMPORT", "import_dir")).resolve()
    extensions = [ext.strip() for ext in config.get("IMPORT", "extensions").split(",")]
    fpaths = []
    for ext in extensions:
        fpaths.extend(input_dir.glob("*." + ext))

    # Read all the files and store as individual .csv files in the csv directory.
    for fpath in sorted(fpaths):
        try:
            import_one(config, fpath)
        except Exception:
            logger.exception("Import failed: ")
            if config.getboolean("IMPORT", "hard_fail"):
                raise
            else:
                failed_dir = Path(config.get("IMPORT", "fail_dir")).resolve()
                dpath = failed_dir / fpath.name
                fpath.rename(dpath)
                logger.info("Failed statement moved to {d}", d=dpath)


if __name__ == "__main__":
    # Get the config
    config_path = Path("") / "config.ini"
    config = read_config(config_path)
    import_all(config)
