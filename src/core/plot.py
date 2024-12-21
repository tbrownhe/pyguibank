from pathlib import Path

import matplotlib.dates as mdates
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.ticker import MultipleLocator

from . import query
from sqlalchemy.orm import Session


def get_balance_data(session: Session) -> None:
    """
    Gets all transactions, makes a pivot table, then plots the result
    to display balance over time.
    """
    # Get all the transactions
    data, columns = query.transactions(session)
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
    asset_dict = query.asset_types(session)
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
    debt_cols.append("Total Debts")

    return df_pivot, debt_cols


def plot_balance_history(session: Session):
    df_pivot, debt_cols = get_balance_data(session)

    # Plot all balances on the same chart
    fig, ax1 = plt.subplots(figsize=(14, 8))
    ax2 = ax1.twinx()
    for account_name in df_pivot.columns.values:
        linestyle = "dashed" if account_name in debt_cols else "solid"
        plt.plot(df_pivot.index, df_pivot[account_name], linestyle=linestyle)

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


def get_category_data(session: Session) -> None:
    """
    Gets all transactions, makes a pivot table, then plots the result
    to display categozied expenses over time.
    """
    # Get all the transactions
    data, columns = query.transactions(session)
    df = pd.DataFrame(data, columns=columns)

    # Create month column for pivot tables
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.to_period("M").astype(str)

    # Make pivot tables
    df_pivot = df.pivot_table(
        index="Month", columns="Category", values="Amount", aggfunc="sum"
    ).fillna(0)

    # df_pivot.index = df_pivot.index + "-15"
    df_pivot.index = pd.to_datetime(df_pivot.index)

    return df_pivot


def plot_category_spending(session: Session):
    # Get data from db
    df_pivot = get_category_data(session)

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
