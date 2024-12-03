from pathlib import Path

from .db import execute_sql_query


def optimize_db(db_path: Path):
    _, _ = execute_sql_query(db_path, "VACUUM")
    _, _ = execute_sql_query(db_path, "ANALYZE")


def statements_containing_hash(db_path: Path, md5hash: str) -> list[tuple]:
    """
    Retrieves StatementID based on the md5hash.
    """
    query = f"SELECT StatementID, Filename FROM Statements WHERE MD5 = '{md5hash}'"
    data, _ = execute_sql_query(db_path, query)
    return data


def statements_containing_filename(db_path: Path, filename: str) -> list[tuple]:
    """
    Retrieves StatementID based on the filename.
    """
    query = (
        f"SELECT StatementID, Filename FROM Statements WHERE Filename = '{filename}'"
    )
    data, _ = execute_sql_query(db_path, query)
    return data


def statement_id(db_path: Path, account_id: int, md5hash: str) -> int:
    """Retrieves unique StatementID based on account_id and md5hash

    Args:
        db_path (Path): _description_
        account_id (int): _description_
        md5hash (str): _description_

    Raises:
        KeyError: _description_
        KeyError: _description_

    Returns:
        int: _description_
    """
    query = (
        "SELECT StatementID FROM Statements"
        f" WHERE AccountID = {account_id} AND MD5 = '{md5hash}'"
    )
    data, _ = execute_sql_query(db_path, query)
    if len(data) == 0:
        raise KeyError(
            "StatementID could not be found for found for"
            f" AccountID = {account_id} and MD5 = '{md5hash}'"
        )
    if len(data) > 1:
        raise KeyError(
            "StatementID is not unique for"
            f" AccountID = {account_id} and MD5 = '{md5hash}'"
        )
    return data[0][0]


def statement_types(db_path: Path, extension=""):
    # Get the list of accounts and search strings from the db.
    query = "SELECT StatementTypeID, SearchString, EntryPoint FROM StatementTypes"
    if extension:
        query += f" WHERE Extension = '{extension}'"
    return execute_sql_query(db_path, query)


def statements(db_path: Path, where="") -> tuple[list[tuple], list[str]]:
    """
    Get the list of statement dates from the db.
    """
    sql_path = Path("") / "src" / "sql" / "statements.sql"
    with sql_path.open("r") as f:
        query = f.read()
    query = query.replace("{where}", where)
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


def account_name(db_path: Path, account_id: int) -> str:
    """
    Retrieves an Account AccountName based on an account string found in a statement.
    """
    query = f"SELECT AccountName FROM Accounts WHERE AccountID = {account_id}"
    data, _ = execute_sql_query(db_path, query)
    if len(data) == 0:
        raise ValueError(f"No Account with AccountID = {account_id}")
    else:
        return data[0][0]


def account_type_id(db_path, account_type):
    query = (
        "SELECT AccountTypeID"
        " FROM AccountTypes"
        f" WHERE AccountType = '{account_type}'"
    )
    data, _ = execute_sql_query(db_path, query)
    if len(data) == 0:
        raise KeyError(f"{account_type} not found in AccountTypes.AccountType")
    else:
        return data[0][0]


def account_names(db_path: Path) -> list[str]:
    """
    Retrieves an Account AccountName based on an account string found in a statement.
    """
    query = f"SELECT AccountName FROM Accounts"
    data, _ = execute_sql_query(db_path, query)
    if len(data) == 0:
        return []
    else:
        return list(row[0] for row in data)


def accounts(db_path: Path) -> tuple[list[tuple], list[str]]:
    query = (
        "SELECT AccountID, AccountName, Company, Description, AccountType"
        " FROM Accounts"
        " JOIN AccountTypes ON Accounts.AccountTypeID = AccountTypes.AccountTypeID"
    )
    return execute_sql_query(db_path, query)


def distinct_categories(db_path: Path) -> list[str]:
    query = "SELECT DISTINCT Category FROM Transactions ORDER BY Category ASC"
    data, _ = execute_sql_query(db_path, query)
    if len(data) == 0:
        return []
    else:
        return [row[0] for row in data]


def transactions(db_path: Path, where="") -> tuple[list[tuple], list[str]]:
    """
    Returns all transactions as pd.DataFrame
    """
    sql_path = Path("") / "src" / "sql" / "transactions.sql"
    with sql_path.open("r") as f:
        query = f.read()
    query = query.replace("{where}", where)
    return execute_sql_query(db_path, query)


def training_set(db_path: Path, where=""):
    query = f"""
    SELECT
        Transactions.TransactionID,
        Accounts.Company,
        AccountTypes.AccountType,
        Transactions.Description,
		Transactions.Amount,
        Transactions.Category
    FROM Transactions
    JOIN Accounts ON Transactions.AccountID = Accounts.AccountID
    JOIN AccountTypes ON Accounts.AccountTypeID = AccountTypes.AccountTypeID
	{where}
    ORDER BY Transactions.Date ASC, Transactions.TransactionID ASC
    """
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
        "SELECT AccountName, AssetType"
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


def latest_balances(db_path: Path):
    """Returns the latest balance and transaction date for each account

    Args:
        db_path (Path): Path to db file

    Returns:
        tuple[list[tuple], list[str]]: data, columns
            (AccountName, LatestBalance, LastTransactionDate)
    """
    query = """
    WITH LatestTransaction AS (
        SELECT 
            AccountID,
            MAX(Date) AS MaxDate
        FROM Transactions
        GROUP BY AccountID
    ),
    LatestTransactionID AS (
        SELECT 
            T.AccountID,
            T.Balance,
            T.TransactionID,
            T.Date
        FROM Transactions T
        JOIN LatestTransaction LT 
            ON T.AccountID = LT.AccountID 
            AND T.Date = LT.MaxDate
        WHERE T.TransactionID = (
            SELECT MAX(TransactionID)
            FROM Transactions T2
            WHERE T2.AccountID = T.AccountID AND T2.Date = T.Date
        )
    )
    SELECT 
        A.AccountName AS AccountName,
        T.Date AS LatestDate,
        T.Balance AS LatestBalance
    FROM Accounts A
    JOIN LatestTransactionID T ON A.AccountID = T.AccountID;
    """
    return execute_sql_query(db_path, query)
