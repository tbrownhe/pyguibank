from pathlib import Path

import pandas as pd
from matplotlib import pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MultipleLocator

from .db import execute_sql_file, execute_sql_query


def get_asset_type() -> dict[str, str]:
    """
    Returns entire contents of Accounts table as a dict
    """
    db_path = Path("") / "pyguibank.db"
    query = "SELECT NickName, AssetType FROM Accounts"
    data, _ = execute_sql_query(db_path, query)
    asset_type = dict(data)
    return asset_type


def get_transactions() -> pd.DataFrame:
    """
    Returns all transactions as pd.DataFrame
    """
    db_path = Path("") / "pyguibank.db"
    sql_path = Path("") / "src" / "sql" / "transactions_all.sql"
    data, columns = execute_sql_file(db_path, sql_path)
    df = pd.DataFrame(data, columns=columns)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.strftime("%Y-%m")
    return df


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


def plot_balances() -> None:
    """
    Gets all transactions, makes a pivot table, then plots the result
    to display balance over time.
    """
    # Get all the transactions
    df = get_transactions()

    # Make a pivot table containing the EOD (last) balance for each day
    df_pivot = df.pivot_table(
        index="Date", columns="NickName", values="Balance", aggfunc="last"
    )

    # Forward fill NaNs, this preserves previously found balances
    df_pivot = df_pivot.ffill(axis=0)

    # Fill any remaining NaNs with zero
    # These are locations where an account doesn't exist yet.
    df_pivot = df_pivot.fillna(0)

    # Create totals columns
    assets = []
    debts = []
    asset_type = get_asset_type()
    for account in df_pivot.columns.values:
        match asset_type[account]:
            case "Asset":
                assets.append(account)
            case "Debt":
                debts.append(account)
            case _:
                raise ValueError("Account %s is neither an asset nor debt." % account)

    df_pivot["Net Worth"] = df_pivot.sum(axis=1)
    df_pivot["Total Assets"] = df_pivot[assets].sum(axis=1)
    df_pivot["Total Debts"] = df_pivot[debts].sum(axis=1)

    fig, ax1 = plt.subplots(figsize=(14, 8))
    ax2 = ax1.twinx()

    # plt.figure(figsize=(14, 8))
    for account in df_pivot.columns.values:
        linestyle = "solid" if asset_type.get(account, "Asset") == "Asset" else "dashed"
        plt.plot(df_pivot.index, df_pivot[account], linestyle=linestyle)

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


def plot_categories() -> None:
    """
    Gets all transactions, makes a pivot table, then plots the result
    to display categozied expenses over time.
    """
    # Get all the transactions
    df = get_transactions()

    # Filter Dates
    df = df[df["Month"] >= "2020-01"]

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
    plot_balances()
    plot_categories()
