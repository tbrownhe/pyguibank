from pathlib import Path

from .db import execute_sql_query


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
