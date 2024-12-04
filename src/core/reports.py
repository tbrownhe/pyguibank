from datetime import datetime
from pathlib import Path

import pandas as pd

from sqlalchemy.orm import Session
from .query import shopping, transactions
from .utils import open_file_in_os


def shopping_report(session: Session, months: int = 12) -> None:
    """
    Saves shopping list as an Excel report for expense tracking.

    Args:
        session (Session): SQLAlchemy session object.
        months (int, optional): Number of months to include in the report. Defaults to 12.
    """
    # Get the shopping data
    data, columns = shopping(session, months=months)
    df = pd.DataFrame(data, columns=columns)

    # Add month column for grouping
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.strftime("%Y-%m")

    # Save as Excel
    output_path = "shopping.xlsx"
    df.to_excel(output_path, index=False)
    print(f"Shopping report saved to {output_path}")


def report(session: Session, dpath: Path, months: int = None):
    # Pull recent transactions and create reports
    data, columns = transactions(session, months=months)
    df = pd.DataFrame(data, columns=columns)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.to_period("M").astype(str)

    # Make pivot tables
    df_pivot = df.pivot_table(
        index="Month", columns="Category", values="Amount", aggfunc="sum"
    ).fillna(0)

    df_pivot_assets = df.pivot_table(
        index="Month", columns=["Category", "AssetType"], values="Amount", aggfunc="sum"
    ).fillna(0)

    # Save to Excel workbook
    with pd.ExcelWriter(path=dpath) as writer:
        df.to_excel(writer, sheet_name="Transactions")
        df_pivot.to_excel(writer, sheet_name="Pivot Category")
        df_pivot_assets.to_excel(writer, "Pivot CategoryAsset")

    # Open new file in Excel
    open_file_in_os(dpath)
