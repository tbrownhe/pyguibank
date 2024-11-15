from datetime import datetime
from pathlib import Path

import pandas as pd

from .query import shopping, transactions
from .utils import open_file_in_os, read_config


def shopping_report(db_path: Path, where=""):
    """
    Saves verbose shopping list as Excel for creating expense reports for wifey <3
    """
    data, columns = shopping(db_path, where)
    df = pd.DataFrame(data, columns=columns)

    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.strftime("%Y-%m")

    df.to_excel("shopping.xlsx", index=False)


def save_pivot_tables(df: pd.DataFrame, timestamp: str) -> None:
    """
    Gets all transactions, makes pivot tables, then saves them to Excel file.
    """


def make_reports(db_path: Path, report_dir: Path):
    # Pull recent transactions and create reports
    data, columns = transactions(db_path, where="WHERE Date >= DATE('now', '-1 year')")
    df = pd.DataFrame(data, columns=columns)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.to_period("M").astype(str)

    # Formatting
    timestamp = datetime.now().strftime(r"%Y%m%d%H%M%S")
    if report_dir.is_file():
        report_dir = report_dir.parents[0]

    # Make pivot tables
    df_pivot = df.pivot_table(
        index="Month", columns="Category", values="Amount", aggfunc="sum"
    ).fillna(0)

    df_pivot_assets = df.pivot_table(
        index="Month", columns=["Category", "AssetType"], values="Amount", aggfunc="sum"
    ).fillna(0)

    # Save to Excel workbook
    dpath = report_dir / f"{timestamp}_report.xlsx"
    with pd.ExcelWriter(path=dpath) as writer:
        df.to_excel(writer, sheet_name="Transactions")
        df_pivot.to_excel(writer, sheet_name="Pivot Category")
        df_pivot_assets.to_excel(writer, "Pivot CategoryAsset")

    open_file_in_os(dpath)


if __name__ == "__main__":
    # Get the db path
    config = read_config(Path("") / "config.ini")
    db_path = Path(config.get("DATABASE", "db_path")).resolve()
    report_dir = Path(config.get("REPORTS", "report_dir")).resolve()
    make_reports(db_path, report_dir)
