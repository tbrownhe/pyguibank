import sqlite3
from datetime import datetime
from typing import Any, Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import asc, distinct, func, or_, select, text

from .orm import (
    AccountNumbers,
    Accounts,
    AccountTypes,
    BaseModel,
    Shopping,
    Statements,
    StatementTypes,
    Transactions,
)


def optimize_db(session: Session) -> None:
    """
    Optimizes the SQLite database by running VACUUM and ANALYZE.

    Args:
        session (Session): The SQLAlchemy session to use for the operation.
    """
    session.execute(text("VACUUM"))
    session.execute(text("ANALYZE"))
    session.commit()


def account_id_of_account_number(session: Session, account_num: str) -> int:
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


def accounts_details(
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
    columns = [column.get("name", "Unknown") for column in query.column_descriptions]

    return data, columns


def account_name_of_account_id(session: Session, account_id: int) -> str:
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


def account_types(session: Session) -> list[str]:
    """
    Retrieves a list of all AccountTypes names.

    Args:
        session (Session): SQLAlchemy session object.

    Returns:
        list[str]: List of account type names.
    """
    account_types = session.query(AccountTypes.AccountType).all()
    return [account_type for (account_type,) in account_types]


def account_types_table(session: Session) -> list[dict]:
    """
    Fetches entire AccountTypes table.

    Args:
        session (Session): SQLAlchemy session object.

    Returns:
        tuple[list[tuple], list[str]]: Data and column names.
    """
    # Perform the query
    query = session.query(
        AccountTypes.AccountTypeID,
        AccountTypes.AccountType,
        AccountTypes.AssetType,
    )

    # Fetch all data
    data = [
        {
            column.get("name", "Unknown"): value
            for column, value in zip(query.column_descriptions, row)
        }
        for row in query.all()
    ]

    return data


def asset_types(session: Session) -> dict[str, str]:
    """
    Returns a dictionary mapping account names to their asset types.

    Args:
        session (Session): SQLAlchemy session object.

    Returns:
        dict[str, str]: A dictionary where keys are account names and values are asset types.
    """
    # Query account names and asset types
    query = session.query(Accounts.AccountName, AccountTypes.AssetType).join(
        AccountTypes, Accounts.AccountTypeID == AccountTypes.AccountTypeID
    )

    # Build the dictionary from query results
    asset_dict = {account_name: asset_type for account_name, asset_type in query.all()}
    return asset_dict


def statement_id_unique(session: Session, account_id: int, md5hash: str) -> int:
    """
    Retrieves unique StatementID based on account_id and md5hash.
    Some statements contain data for multiple accounts, and each account
    within statement gets a line in the Statements table, so the statement
    md5hash alone is not unique.

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


def statement_date_ranges(
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
    columns = [column.get("name", "Unknown") for column in query.column_descriptions]

    return data, columns


def statements_with_hash(session: Session, md5hash: str) -> list[tuple]:
    """
    Retrieves StatementID and Filename based on the md5hash.

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


def statements_with_filename(session: Session, filename: str) -> list[tuple]:
    """
    Retrieves StatementID and Filename based on the filename.

    Args:
        session (Session): The SQLAlchemy session to use for the query.
        filename (str): The filename to search for.

    Returns:
        list[tuple]: A list of (StatementID, Filename) tuples.
    """
    try:
        results = session.execute(
            select(Statements.StatementID, Statements.Filename).where(
                Statements.Filename == filename
            )
        ).all()
        return results
    except SQLAlchemyError as e:
        session.rollback()
        raise RuntimeError(f"Database query failed: {e}")


def statement_type_routing(
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


def statement_types_table(session: Session) -> list[dict]:
    """
    Fetches entire StatementTypes table.

    Args:
        session (Session): SQLAlchemy session object.

    Returns:
        tuple[list[tuple], list[str]]: Data and column names.
    """
    # Perform the query
    query = session.query(
        StatementTypes.AccountTypeID,
        StatementTypes.Company,
        StatementTypes.Description,
        StatementTypes.Extension,
        StatementTypes.SearchString,
        StatementTypes.Parser,
        StatementTypes.EntryPoint,
    )

    # Fetch all data
    data = [
        {
            column.get("name", "Unknown"): value
            for column, value in zip(query.column_descriptions, row)
        }
        for row in query.all()
    ]

    return data


def statement_type_details(session: Session, stid: int) -> tuple[str, str, str]:
    """
    Fetches company, description, and account type for a given StatementTypeID.

    Args:
        session (Session): SQLAlchemy session object.
        statement_type_id (int): The StatementTypeID to filter on.

    Returns:
        dict: A dictionary containing Company, Description, and AccountType.
    """
    result = (
        session.query(
            StatementTypes.Company,
            StatementTypes.Description,
            AccountTypes.AccountType,
        )
        .join(AccountTypes, StatementTypes.AccountTypeID == AccountTypes.AccountTypeID)
        .filter(StatementTypes.StatementTypeID == stid)
        .one_or_none()
    )
    if not result:
        raise ValueError(f"StatementTypeID {stid} not found in StatementTypes.")
    return result


def transactions(session: Session, months: int = None) -> tuple[list[tuple], list[str]]:
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
    columns = [column.get("name", "Unknown") for column in query.column_descriptions]

    return data, columns


def latest_balance(session: Session, account_id: int) -> Optional[tuple[str, float]]:
    """
    Retrieves the most recent balance and transaction date for a given account.

    Args:
        session (Session): SQLAlchemy session object.
        account_id (int): The AccountID to query.

    Returns:
        Optional[tuple[str, float]]: A tuple containing the most recent transaction date
        and balance, or None if no transactions exist for the account.
    """
    result = (
        session.query(Transactions.Date, Transactions.Balance)
        .filter(Transactions.AccountID == account_id)
        .order_by(Transactions.Date.desc(), Transactions.TransactionID.desc())
        .first()
    )

    return result


def latest_balances(session: Session) -> list[tuple[str, str, float]]:
    """
    Retrieves the latest balance and transaction date for each account.

    Args:
        session (Session): SQLAlchemy session object.

    Returns:
        list[tuple[str, str, float]]: A list of tuples containing:
            (AccountName, LatestDate, LatestBalance)
    """
    # Subquery: LatestTransaction
    subquery = (
        session.query(
            Transactions.AccountID,
            func.max(Transactions.Date).label("LatestDate"),
        )
        .group_by(Transactions.AccountID)
        .subquery()
    )

    # Subquery: LatestTransactionWithID
    latest_transaction = (
        session.query(
            Transactions.AccountID,
            Transactions.TransactionID,
        )
        .join(subquery, subquery.c.AccountID == Transactions.AccountID)
        .filter(Transactions.Date == subquery.c.LatestDate)
        .group_by(Transactions.AccountID)
        .having(func.max(Transactions.TransactionID))
        .subquery()
    )

    # Main query: Join with Accounts and get the latest balance
    query = (
        session.query(
            Accounts.AccountName,
            Transactions.Balance,
            subquery.c.LatestDate,
        )
        .join(Transactions, Transactions.AccountID == Accounts.AccountID)
        .join(subquery, subquery.c.AccountID == Transactions.AccountID)
        .join(
            latest_transaction,
            latest_transaction.c.TransactionID == Transactions.TransactionID,
        )
    )

    return query.all()


def training_set(
    session: Session,
    verified: bool = False,
    unverified: bool = False,
    categorized: bool = False,
    uncategorized: bool = False,
) -> tuple[list[tuple], list[str]]:
    """
    Retrieves a training set of transaction data with flexible filtering options.
    Returns all transactions if no flags are set.

    Args:
        session (Session): SQLAlchemy session object.
        verified (bool, optional): Include only verified transactions if True. Defaults to False.
        unverified (bool, optional): Include only unverified transactions if True. Defaults to False.
        categorized (bool, optional): Include only categorized transactions if True. Defaults to False.
        uncategorized (bool, optional): Include only uncategorized transactions if True. Defaults to False.

    Raises:
        ValueError: If verified and unverified are both True.
        ValueError: If categorized and uncategorized are both True.

    Returns:
        tuple[list[tuple], list[str]]: A list of training data and column names.

    Notes:
        By default, if no filters are applied, all transactions are returned.
        Results are sorted by Date (ascending) and TransactionID (ascending).
    """
    # Validate input
    if verified and unverified:
        raise ValueError("verified and unverified flags cannot both be True")
    if categorized and uncategorized:
        raise ValueError("categorized and uncategorized flags cannot both be True")

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

    # Apply filters
    if verified:
        query = query.filter(Transactions.Verified == 1)
    elif unverified:
        query = query.filter(Transactions.Verified == 0)

    if categorized:
        uncategorized_filter = or_(
            Transactions.Category == "Uncategorized",
            Transactions.Category == "",
            Transactions.Category.is_(None),
        )
        query = query.filter(~uncategorized_filter)
    elif uncategorized:
        uncategorized_filter = or_(
            Transactions.Category == "Uncategorized",
            Transactions.Category == "",
            Transactions.Category.is_(None),
        )
        query = query.filter(uncategorized_filter)

    # Execute query and fetch results
    data = query.all()
    columns = [column.get("name", "Unknown") for column in query.column_descriptions]

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


def shopping(session: Session, months: int = 12) -> tuple[list[tuple], list[str]]:
    """
    Retrieves a list of Shopping data for the last number of months.

    Args:
        session (Session): SQLAlchemy session object.
        months (int, optional): Number of months to include in the report. Defaults to 12.

    Returns:
        tuple[list[tuple], list[str]]: A list of training data and column names.
    """
    # Query shopping transactions
    query = (
        session.query(
            Shopping.ItemID,
            Accounts.AccountName,
            Shopping.Date,
            Shopping.Amount,
            Shopping.Description,
            Shopping.Category,
        )
        .join(Accounts, Shopping.AccountID == Accounts.AccountID)
        .filter(Shopping.Date >= func.date("now", f"-{months} months"))
        .order_by(asc(Shopping.Date), asc(Shopping.ItemID))
    )

    # Fetch results
    data = query.all()
    columns = [column.get("name", "Unknown") for column in query.column_descriptions]

    return data, columns


def insert_rows_batched(session: Session, model: BaseModel, rows: list[dict]) -> None:
    """
    Performs batched insertion of rows, rolling back the transaction if any error occurs.

    Args:
        session (Session): SQLAlchemy session object.
        model (BaseModel): SQLAlchemy model representing the table.
        rows (list[dict]): List of dictionaries representing rows to insert.

    Raises:
        IntegrityError: If the insertion fails, the entire batch is rolled back.
    """
    try:
        objects = [model(**row) for row in rows]
        session.bulk_save_objects(objects)
        session.commit()
    except sqlite3.IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"Batch insertion failed: {e}")


def insert_rows_carefully(
    session: Session,
    model: BaseModel,
    data: list[dict[str, Any]],
    skip_duplicates: bool = False,
) -> None:
    """
    Insert rows into the database with optional duplicate handling.

    Args:
        session (Session): SQLAlchemy session.
        model (Type[Base]): SQLAlchemy ORM model for the target table.
        data (List[Dict[str, Any]]): List of data rows to insert as dictionaries.
        skip_duplicates (bool): Whether to skip duplicate rows.

    Returns:
        None
    """
    skipped = 0

    for row in data:
        try:
            session.add(model(**row))
        except sqlite3.IntegrityError:
            if skip_duplicates:
                skipped += 1
            else:
                raise

    if skip_duplicates and skipped > 0:
        logger.info(
            f"Skipped {skipped} duplicate rows while inserting {len(data)} rows"
            f" into {model.__tablename__}. "
        )


def update_db_where(
    session: Session,
    model: BaseModel,
    update_cols: list[str],
    update_list: list[tuple],
    where_cols: list[str],
    where_list: list[tuple],
) -> None:
    """
    Updates rows of data in an SQLAlchemy-managed database table.

    Args:
        session (Session): SQLAlchemy session object.
        model (BaseModel): SQLAlchemy ORM model class representing the table.
        update_cols (list[str]): Columns to update.
        update_list (list[tuple]): Values to update in the corresponding columns.
        where_cols (list[str]): Columns for the WHERE clause.
        where_list (list[tuple]): Values for the WHERE clause.
    """
    if len(update_list) != len(where_list):
        raise ValueError("Length of update_list and where_list must be equal.")

    for update_vals, where_vals in zip(update_list, where_list):
        # Build the WHERE clause dynamically
        conditions = [
            getattr(model, col) == val for col, val in zip(where_cols, where_vals)
        ]

        # Update the rows matching the conditions
        session.query(model).filter(*conditions).update(
            {getattr(model, col): val for col, val in zip(update_cols, update_vals)},
            synchronize_session="fetch",  # Ensures in-memory consistency
        )

    session.commit()
