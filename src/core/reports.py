from pathlib import Path

import pandas as pd

from .db import execute_sql_query
from .utils import read_config


def get_transactions(db_path: Path, where="") -> pd.DataFrame:
    """
    Returns all transactions as pd.DataFrame
    """
    if where:
        sql_path = Path("") / "src" / "sql" / "transactions_where.sql"
    else:
        sql_path = Path("") / "src" / "sql" / "transactions.sql"
    with sql_path.open("r") as f:
        query = f.read()

    if where:
        query = query.replace("$$WH$$", where)

    data, columns = execute_sql_query(db_path, query)
    df = pd.DataFrame(data, columns=columns)

    # Create month column for pivot tables
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.to_period("M").astype(str)

    return df


def get_shopping(db_path: Path, where: str) -> pd.DataFrame:
    """
    Returns all transactions as pd.DataFrame
    """
    sql_path = Path("") / "src" / "sql" / "shopping_where.sql"
    with sql_path.open("r") as f:
        query = f.read()
    query = query % where
    data, columns = execute_sql_query(db_path, query)
    df = pd.DataFrame(data, columns=columns)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.strftime("%Y-%m")
    return df


def shopping_report(where: str):
    """
    Saves verbose shopping list as Excel for creating expense reports for wifey <3
    """
    df = get_shopping(where)
    df = df.sort_values(by=["Date", "ItemID"], axis=0)
    df.to_excel("shopping.xlsx", index=False)


def pivot_tables(df: pd.DataFrame) -> None:
    """
    Gets all transactions, makes pivot tables, then saves them to Excel file.
    """
    # Make pivot tables
    df_pivot = df.pivot_table(
        index="Month", columns="Category", values="Amount", aggfunc="sum"
    ).fillna(0)

    df_pivot_assets = df.pivot_table(
        index="Month", columns=["Category", "AssetType"], values="Amount", aggfunc="sum"
    ).fillna(0)

    # Save to Excel workbook
    with pd.ExcelWriter(path="pivot_tables.xlsx") as writer:
        df_pivot.to_excel(writer, sheet_name="Category")
        df_pivot_assets.to_excel(writer, "CategoryAsset")


def make_reports():
    # Get the db path
    config = read_config(Path("") / "config.ini")
    db_path = Path(config.get("DATABASE", "db_path")).resolve()

    # Pull recent transactions and create reports
    df = get_transactions(db_path, where="Date >= DATE('now', '-1 year')")
    df.to_excel("transactions.xlsx", index=False)
    pivot_tables(df)


if __name__ == "__main__":
    reports()
