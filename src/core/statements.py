# -*- coding: utf-8 -*-
import csv
import hashlib
import shutil
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path

from loguru import logger

from core.db import execute_sql_query, insert_into_db
from core.parse import parse
from core.utils import read_config


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


def get_account_id(db_path: Path, account_num: str) -> int:
    """
    Retrieves an AccountID based on an account string found in a statement.
    """
    query = (
        "SELECT AccountID FROM AccountNumbers WHERE AccountNumber = '%s'" % account_num
    )
    data, _ = execute_sql_query(db_path, query)
    if len(data) == 0:
        raise ValueError("'%s' not found in Accounts table." % account_num)
    else:
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
    main_account_id: int,
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
        "STID",
        "MainAccountID",
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
        main_account_id,
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


def get_account_info(
    db_path: Path, account_nums: list[str]
) -> tuple[dict[str, int], str]:
    """
    Makes sure all accounts in the statement have an entry in the lookup table.
    Return the nicknames of all accounts
    """
    account_ids = {}
    for account_num in account_nums:
        account_id = get_account_id(db_path, account_num)
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
    shutil.move(fpath, dpath)


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
    account_ids, nick_name = get_account_info(db_path, list(data.keys()))

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
    move_to_archive(fpath, Path(config.get("SETTINGS", "success_dir")), new_fname)


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
                return
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
