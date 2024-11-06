from db import execute_sql_query
from pathlib import Path
import pandas as pd


def get_transactions(where: str) -> pd.DataFrame:
    """
    Returns all transactions as pd.DataFrame
    """
    db_path = Path("") / "pyguibank.db"
    sql_path = Path("") / "src" / "sql" / "transactions_where.sql"
    with sql_path.open("r") as f:
        query = f.read()
    query = query % where
    data, columns = execute_sql_query(db_path, query)
    df = pd.DataFrame(data, columns=columns)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.strftime("%Y-%m")
    return df


def get_shopping(where: str) -> pd.DataFrame:
    """
    Returns all transactions as pd.DataFrame
    """
    db_path = Path("") / "pyguibank.db"
    sql_path = Path("") / "src" / "sql" / "shopping_where.sql"
    with sql_path.open("r") as f:
        query = f.read()
    query = query % where
    data, columns = execute_sql_query(db_path, query)
    df = pd.DataFrame(data, columns=columns)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.strftime("%Y-%m")
    return df


def transaction_report(df: pd.DataFrame):
    """
    Saves verbose transaction list as Excel for creating expense reports for wifey <3
    """
    df = df.sort_values(by=["Date", "TranID"], axis=0)
    df.to_excel("transactions.xlsx", index=False)


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


def reports():
    # Get all the transactions
    # where = "Date >= '2022-08' AND Date < '2022-11'"
    where = "Date >= '2024'"
    if True:
        df = get_transactions(where)
        transaction_report(df)
        pivot_tables(df)

    if False:
        shopping_report("Date >= '2022-08' AND Date < '2023-03'")


if __name__ == "__main__":
    reports()
