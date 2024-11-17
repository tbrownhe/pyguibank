from pathlib import Path

from .db import execute_sql_query


def statement_id(db_path: Path, md5hash: str) -> int:
    """
    Retrieves a StatementID based on the md5hash.
    """
    query = f"SELECT StatementID FROM Statements WHERE MD5 = '{md5hash}'"
    data, _ = execute_sql_query(db_path, query)
    if len(data) == 0:
        return -1
    elif len(data) == 1:
        return data[0][0]
    else:
        raise KeyError(f"{md5hash} is not unique in Statements.MD5.")


def statement_types(db_path: Path, extension=""):
    # Get the list of accounts and search strings from the db.
    query = "SELECT StatementTypeID, SearchString, Parser FROM StatementTypes"
    if extension:
        query += f" WHERE Extension = '{extension}'"
    return execute_sql_query(db_path, query)


def account_id(db_path: Path, account_num: str) -> int:
    """
    Retrieves an AccountID based on an account_num string found in a statement.
    """
    query = (
        f"SELECT AccountID FROM AccountNumbers WHERE AccountNumber = '{account_num}'"
    )
    data, _ = execute_sql_query(db_path, query)
    if len(data) == 0:
        raise KeyError(f"{account_num} not found in AccountNumbers.AccountNumber")
    return data[0][0]


def account_nickname(db_path: Path, account_id: int) -> str:
    """
    Retrieves an Account Nickname based on an account string found in a statement.
    """
    query = f"SELECT NickName FROM Accounts WHERE AccountID = {account_id}"
    data, _ = execute_sql_query(db_path, query)
    if len(data) == 0:
        raise ValueError(f"No Account with AccountID = {account_id}")
    else:
        return data[0][0]


def accounts(db_path: Path) -> tuple[list[tuple], list[str]]:
    query = (
        "SELECT AccountID, Company, Description, AccountType, NickName"
        " FROM Accounts"
        " JOIN AccountTypes ON Accounts.AccountTypeID = AccountTypes.AccountTypeID"
    )
    return execute_sql_query(db_path, query)


def transactions(db_path: Path, where="") -> tuple[list[tuple], list[str]]:
    """
    Returns all transactions as pd.DataFrame
    """
    sql_path = Path("") / "src" / "sql" / "transactions.sql"
    with sql_path.open("r") as f:
        query = f.read()
    query = query.replace("{where}", where)
    return execute_sql_query(db_path, query)


def shopping(db_path: Path, where="") -> tuple[list[tuple], list[str]]:
    """
    Returns all transactions as pd.DataFrame
    """
    sql_path = Path("") / "src" / "sql" / "shopping.sql"
    with sql_path.open("r") as f:
        query = f.read()
    query = query.replace("{where}", where)
    return execute_sql_query(db_path, query)


def asset_types(db_path: Path) -> dict[str, str]:
    """
    Returns Asset Type of Accounts table as df
    """
    query = (
        "SELECT NickName, AssetType"
        " FROM Accounts"
        " JOIN AccountTypes ON Accounts.AccountTypeID = AccountTypes.AccountTypeID"
    )
    data, _ = execute_sql_query(db_path, query)
    asset_dict = {}
    for row in data:
        asset_dict[row[0]] = row[1]
    return asset_dict


def latest_balance(db_path: Path, account_id: int) -> dict[str, str]:
    query = (
        "SELECT Date, Balance FROM Transactions"
        f" WHERE AccountID = {account_id}"
        " ORDER BY Date DESC, TransactionID DESC"
        " LIMIT 1"
    )
    return execute_sql_query(db_path, query)
