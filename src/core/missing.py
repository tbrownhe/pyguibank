from datetime import timedelta
from pathlib import Path

import pandas as pd

from .query import statements


def get_missing_coverage(db_path: Path):
    """
    Returns a DataFrame showing coverage for the first of the month for each account.
    """
    data, columns = statements(db_path)
    df = pd.DataFrame(data, columns=columns)
    df["StartDate"] = pd.to_datetime(df["StartDate"])
    df["EndDate"] = pd.to_datetime(df["EndDate"])

    start_date = df["StartDate"].min() - timedelta(weeks=4)
    end_date = df["EndDate"].max() + timedelta(weeks=4)
    date_range = pd.date_range(start_date, end_date, freq="D")
    nick_names = df["NickName"].unique()
    df_missing = pd.DataFrame(False, index=date_range, columns=nick_names)

    # Set all days that have statement coverage to True
    for i in range(len(df)):
        account = df["NickName"].iloc[i]
        start_date = df["StartDate"].iloc[i]
        end_date = df["EndDate"].iloc[i]
        df_missing.loc[start_date:end_date, account] = True

    # Stack the table so coverage is all in a single column
    df_stacked = (
        df_missing.stack()
        .reset_index()
        .rename(columns={"level_0": "Date", "level_1": "NickName", 0: "Coverage"})
    )

    # Add a month column
    df_stacked["Month"] = df_stacked["Date"].dt.strftime(r"%Y-%m-01")

    # Make a pivot table showing coverage for the first of the month
    df_pivot = df_stacked.pivot_table(
        values="Coverage", index="Month", columns="NickName", aggfunc="first"
    )

    # Return the last 13 months as a transposed DataFrame
    return df_pivot.tail(13).T
