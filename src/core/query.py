from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import asc, distinct, func, or_, select

from src.core.orm import Accounts, AccountTypes, Transactions

from .orm import AccountNumbers, Accounts, AccountTypes, Statements, StatementTypes


def optimize_db(session: Session) -> None:
    """
    Optimizes the SQLite database by running VACUUM and ANALYZE.

    Args:
        session (Session): The SQLAlchemy session to use for the operation.
    """
    session.execute("VACUUM")
    session.execute("ANALYZE")
    session.commit()


def statements_containing_hash(session: Session, md5hash: str) -> list[tuple]:
    """
    Retrieves StatementID and Filename based on the md5hash using SQLAlchemy ORM.

    Args:
        session (Session): SQLAlchemy session for database interaction.
        md5hash (str): The MD5 hash to filter by.

    Returns:
        list[tuple]: A list of tuples containing StatementID and Filename.
    """
    try:
        results = (
            session.query(Statements.StatementID, Statements.Filename)
            .filter(Statements.MD5 == md5hash)
            .all()
        )
        return results
    except SQLAlchemyError as e:
        session.rollback()
        raise RuntimeError(f"Database query failed: {e}")


def statements_containing_filename(session: Session, filename: str) -> list[tuple]:
    """
    Retrieves StatementID and Filename based on the filename.

    Args:
        session (Session): The SQLAlchemy session to use for the query.
        filename (str): The filename to search for.

    Returns:
        list[tuple]: A list of (StatementID, Filename) tuples.
    """
    results = session.execute(
        select(Statements.StatementID, Statements.Filename).where(
            Statements.Filename == filename
        )
    ).all()
    return results


def statement_id(session: Session, account_id: int, md5hash: str) -> int:
    """
    Retrieves unique StatementID based on account_id and md5hash.

    Args:
        session (Session): The SQLAlchemy session to use for the query.
        account_id (int): The ID of the account.
        md5hash (str): The MD5 hash of the statement.

    Raises:
        KeyError: If no matching StatementID is found or if multiple matches are found.

    Returns:
        int: The unique StatementID.
    """
    results = (
        session.execute(
            select(Statements.StatementID).where(
                Statements.AccountID == account_id, Statements.MD5 == md5hash
            )
        )
        .scalars()
        .all()
    )

    if len(results) == 0:
        raise KeyError(
            "StatementID could not be found for AccountID"
            f" = {account_id} and MD5 = '{md5hash}'"
        )
    if len(results) > 1:
        raise KeyError(
            "StatementID is not unique for"
            f" AccountID = {account_id} and MD5 = '{md5hash}'"
        )
    return results[0]


def account_types(session: Session) -> list[str]:
    """
    Retrieves a list of all AccountType names.

    Args:
        session (Session): SQLAlchemy session object.

    Returns:
        list[str]: List of account type names.
    """
    account_types = session.query(AccountTypes.AccountType).all()
    return [account_type for (account_type,) in account_types]


def statement_types(
    session: Session, extension: str = ""
) -> list[tuple[int, str, str]]:
    """
    Retrieves StatementTypeID, SearchString, and EntryPoint from the StatementTypes table.
    Optionally filters by extension.

    Args:
        session (Session): The SQLAlchemy session to use for the query.
        extension (str, optional): The file extension to filter by. Defaults to "".

    Returns:
        list[tuple[int, str, str]]: A list of tuples containing StatementTypeID, SearchString, and EntryPoint.
    """
    query = select(
        StatementTypes.StatementTypeID,
        StatementTypes.SearchString,
        StatementTypes.EntryPoint,
    )
    if extension:
        query = query.where(StatementTypes.Extension == extension)

    return session.execute(query).fetchall()


def statements(
    session: Session, months: int = 15
) -> tuple[list[tuple[str, datetime, datetime]], list[str]]:
    """
    Get the list of statement dates joined with account names.

    Args:
        session (Session): The SQLAlchemy session object.
        months (int): Number of months to filter from the current date.

    Returns:
        tuple[list[tuple[str, datetime, datetime]], list[str]]: Data and column names
    """
    query = (
        session.query(Accounts.AccountName, Statements.StartDate, Statements.EndDate)
        .join(Accounts, Statements.AccountID == Accounts.AccountID)
        .filter(Statements.StartDate >= func.date("now", f"-{months} months"))
        .order_by(Accounts.AccountName.asc(), Statements.StartDate.asc())
    )

    data = query.all()
    columns = [column.key for column in query.column_descriptions]

    return data, columns


def account_id(session: Session, account_num: str) -> int:
    """
    Retrieves an AccountID based on an account_num string found in a statement.

    Args:
        session (Session): SQLAlchemy session object.
        account_num (str): Account number to look up.

    Returns:
        int: AccountID corresponding to the provided account number.

    Raises:
        KeyError: If the account number is not found.
    """
    account_number = (
        session.query(AccountNumbers.AccountID)
        .filter(AccountNumbers.AccountNumber == account_num)
        .one_or_none()
    )

    if account_number is None:
        raise KeyError(f"{account_num} not found in AccountNumbers.AccountNumber")

    return account_number[0]


def account_name(session: Session, account_id: int) -> str:
    """
    Retrieves an AccountName based on an AccountID.

    Args:
        session (Session): SQLAlchemy session object.
        account_id (int): The AccountID to look up.

    Returns:
        str: The AccountName corresponding to the provided AccountID.

    Raises:
        ValueError: If no account is found with the given AccountID.
    """
    account = (
        session.query(Accounts.AccountName)
        .filter(Accounts.AccountID == account_id)
        .one_or_none()
    )

    if account is None:
        raise ValueError(f"No Account with AccountID = {account_id}")

    return account[0]


def account_type_id(session: Session, account_type: str) -> int:
    """
    Retrieves an AccountTypeID based on the AccountType name.

    Args:
        session (Session): SQLAlchemy session object.
        account_type (str): The name of the account type to look up.

    Returns:
        int: The AccountTypeID corresponding to the provided account type.

    Raises:
        KeyError: If no account type is found with the given name.
    """
    account_type_entry = (
        session.query(AccountTypes.AccountTypeID)
        .filter(AccountTypes.AccountType == account_type)
        .one_or_none()
    )

    if account_type_entry is None:
        raise KeyError(f"{account_type} not found in AccountTypes.AccountType")

    return account_type_entry[0]


def account_names(session: Session) -> list[str]:
    """
    Retrieves a list of all Account Names.

    Args:
        session (Session): SQLAlchemy session object.

    Returns:
        list[str]: List of account names.
    """
    account_names = session.query(Accounts.AccountName).all()
    return [name for (name,) in account_names]


def accounts(
    session: Session,
) -> tuple[list[tuple[int, str, str, str, str]], list[str]]:
    """
    Retrieves all account details, including the account type name.

    Args:
        session (Session): SQLAlchemy session object.

    Returns:
        tuple[list[tuple[int, str, str, str, str]], list[str]]:
            Data and column names.
    """
    query = session.query(
        Accounts.AccountID,
        Accounts.AccountName,
        Accounts.Company,
        Accounts.Description,
        AccountTypes.AccountType,
    ).join(AccountTypes, Accounts.AccountTypeID == AccountTypes.AccountTypeID)

    data = query.all()
    columns = [column.key for column in query.column_descriptions]

    return data, columns


def distinct_categories(session: Session) -> list[str]:
    """
    Retrieves a list of distinct transaction categories.

    Args:
        session (Session): SQLAlchemy session object.

    Returns:
        list[str]: A sorted list of distinct transaction categories.
    """
    query = session.query(distinct(Transactions.Category)).order_by(
        asc(Transactions.Category)
    )
    data = query.all()
    return [category[0] for category in data]


def transactions(session: Session, months: int = None) -> list[tuple]:
    """
    Retrieves all transactions with associated account and account type details.

    Args:
        session (Session): SQLAlchemy session object.
        months (int, optional): The number of months from the current date to filter transactions.
            If None, retrieves all transactions.

    Returns:
        tuple[list[tuple], list[str]]: Data and column names.
    """
    # Build the base query
    query = (
        session.query(
            Transactions.TransactionID,
            Accounts.AccountName,
            AccountTypes.AssetType,
            Transactions.Date,
            Transactions.Amount,
            Transactions.Balance,
            Transactions.Description,
            Transactions.Category,
        )
        .join(Accounts, Transactions.AccountID == Accounts.AccountID)
        .join(AccountTypes, Accounts.AccountTypeID == AccountTypes.AccountTypeID)
        .order_by(asc(Transactions.Date), asc(Transactions.TransactionID))
    )

    # Apply date filtering if months is specified
    if months is not None:
        query = query.filter(Transactions.Date >= func.date("now", f"-{months} month"))

    # Execute the query and fetch results
    data = query.all()
    columns = [column.key for column in query.column_descriptions]

    return data, columns


def training_set(
    session: Session,
    verified: bool = True,
    uncategorized: bool = False,
) -> tuple[list[tuple], list[str]]:
    """
    Retrieves a training set of transaction data with flexible filtering options.

    Args:
        session (Session): SQLAlchemy session object.
        verified (bool, optional): Filter by verification status. If None, ignore this filter.
        include_uncategorized (bool, optional): Include only uncategorized transactions.

    Returns:
        tuple[list[tuple], list[str]]: A list of training data and column names.
    """
    # Base query
    query = (
        session.query(
            Transactions.TransactionID,
            Accounts.Company,
            AccountTypes.AccountType,
            Transactions.Description,
            Transactions.Amount,
            Transactions.Category,
        )
        .join(Accounts, Transactions.AccountID == Accounts.AccountID)
        .join(AccountTypes, Accounts.AccountTypeID == AccountTypes.AccountTypeID)
        .order_by(asc(Transactions.Date), asc(Transactions.TransactionID))
    )

    # Apply verified filter
    query = query.filter(Transactions.Verified == (1 if verified else 0))

    # Apply uncategorized filter
    if uncategorized:
        query = query.filter(
            or_(
                Transactions.Category == "Uncategorized",
                Transactions.Category == "",
                Transactions.Category.is_(None),
            )
        )

    # Execute query and fetch results
    data = query.all()
    columns = [column.key for column in query.column_descriptions]

    return data, columns


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
