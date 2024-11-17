from pathlib import Path

import matplotlib.dates as mdates
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.ticker import MultipleLocator

from . import query
from .utils import read_config

r"""
def auto_depreciation(df_auto: pd.DataFrame) -> pd.DataFrame:
    # Calulate Auto depreciated value
    even_data["Auto Resale"] = 0
    depreciation = -2998
    row = np.argmin(even_data["AUTO"].values)
    orig_value = -even_data["AUTO"].iloc[row]
    AUTO = even_data["AUTO"]
    AUTO = AUTO[row : len(even_data)].values
    AUTO = np.round(orig_value * np.exp(np.arange(0, len(AUTO), 1) / depreciation), 2)
    AUTO = np.concatenate((np.zeros([row]), AUTO))

    even_data["Auto Resale"] = AUTO

    return
"""


def balances(db_path: Path) -> None:
    """
    Gets all transactions, makes a pivot table, then plots the result
    to display balance over time.
    """

    # Get all the transactions
    data, columns = query.transactions(db_path)
    df = pd.DataFrame(data, columns=columns)
    df["Date"] = pd.to_datetime(df["Date"])

    # Make a pivot table containing the EOD (last) balance for each day
    df_pivot = df.pivot_table(
        index="Date", columns="AccountName", values="Balance", aggfunc="last"
    )

    # Forward fill NaNs, this preserves previously found balances
    df_pivot = df_pivot.ffill(axis=0)

    # Fill any remaining NaNs with zero
    # These are locations where an account doesn't exist yet.
    df_pivot = df_pivot.fillna(0)

    # Determine which columns in the pivot table are assets and debts
    asset_cols = []
    debt_cols = []
    asset_dict = query.asset_types(db_path)
    for nick_name in df_pivot.columns.values:
        match asset_dict[nick_name]:
            case "Asset":
                asset_cols.append(nick_name)
            case "Debt":
                debt_cols.append(nick_name)
            case _:
                raise ValueError(f"Account {nick_name} is neither an asset nor debt.")

    # Compute total assets and debts
    df_pivot["Net Worth"] = df_pivot.sum(axis=1)
    df_pivot["Total Assets"] = df_pivot[asset_cols].sum(axis=1)
    df_pivot["Total Debts"] = df_pivot[debt_cols].sum(axis=1)
    # asset_dict["Net Worth"] = "Asset"
    # asset_dict["Total Assets"] = "Asset"
    # asset_dict["Total Debts"] = "Debt"

    # Plot all balances on the same chart
    fig, ax1 = plt.subplots(figsize=(14, 8))
    ax2 = ax1.twinx()
    for nick_name in df_pivot.columns.values:
        linestyle = (
            "dashed" if asset_dict.get(nick_name, "Asset") == "Debt" else "solid"
        )
        plt.plot(df_pivot.index, df_pivot[nick_name], linestyle=linestyle)

    # Set bottom right cursor info to contain full datetime string instead of YYYY
    ax1.fmt_xdata = lambda x: mdates.num2date(x).strftime(r"%Y-%m-%d")

    # Add horizontal gridlines every 25,000 units
    major_locator = MultipleLocator(base=25000)
    ax1.yaxis.set_major_locator(major_locator)
    ax2.yaxis.set_major_locator(major_locator)

    # Hide the tick labels on the left axis
    ax1.yaxis.set_tick_params(labelleft=False)

    # Add labels and show plot
    plt.legend(df_pivot.columns.values)
    plt.xlabel("Date")
    plt.ylabel("Balance ($)")
    plt.show()


def categories(db_path: Path) -> None:
    """
    Gets all transactions, makes a pivot table, then plots the result
    to display categozied expenses over time.
    """
    # Get all the transactions
    data, columns = query.transactions(
        db_path, where="WHERE Date >= DATE('now', '-4 year')"
    )
    df = pd.DataFrame(data, columns=columns)

    # Create month column for pivot tables
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.to_period("M").astype(str)

    # Make pivot tables
    df_pivot_detail = df.pivot_table(
        index="Month", columns=["AssetType", "Category"], values="Amount", aggfunc="sum"
    ).fillna(0)
    df_pivot = df.pivot_table(
        index="Month", columns="Category", values="Amount", aggfunc="sum"
    ).fillna(0)

    with pd.ExcelWriter(path="pivot_tables.xlsx") as writer:
        df_pivot.to_excel(writer, sheet_name="Category")
        df_pivot_detail.to_excel(writer, "Category_Asset")

    df_pivot.index = df_pivot.index + "-15"
    df_pivot.index = pd.to_datetime(df_pivot.index)

    plt.figure(figsize=(14, 8))
    for category in df_pivot.columns.values:
        # df_pivot[category].ewm(span=3).mean().plot()
        df_pivot[category].plot()

    # plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    # plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.gca().fmt_xdata = lambda x: mdates.num2date(x).strftime(r"%Y-%m")

    plt.legend(df_pivot.columns.values)
    plt.xlabel("Date")
    plt.xticks(rotation=90)
    plt.ylabel("Amount ($)")
    plt.show()


if __name__ == "__main__":
    # Plot account balances over time
    config = read_config(Path("") / "config.ini")
    db_path = Path(config.get("DATABASE", "db_path")).resolve()
    balances(db_path)
    categories(db_path)
