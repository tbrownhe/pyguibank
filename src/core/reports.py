from datetime import datetime
from pathlib import Path

import pandas as pd

from sqlalchemy.orm import Session
from .query import shopping, transactions
from .utils import open_file_in_os


def shopping_report(session: Session, where=""):
    """
    Saves verbose shopping list as Excel for creating expense reports for wifey <3
    """
    data, columns = shopping(session, where)
    df = pd.DataFrame(data, columns=columns)

    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.strftime("%Y-%m")

    df.to_excel("shopping.xlsx", index=False)


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
