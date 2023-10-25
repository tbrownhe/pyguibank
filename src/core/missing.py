import time
import os
import warnings
import webbrowser
from datetime import timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd

from .db import execute_sql_file, execute_sql_query


def get_statements(where=None):
    """
    Get the list of statement dates from the db.
    """
    db_path = Path("") / "pyguibank.db"
    if where:
        sql_path = Path("") / "src" / "sql" / "statements_where.sql"
        with sql_path.open("r") as f:
            query = f.read()
        query = query % where
        data, columns = execute_sql_query(db_path, query)
    else:
        sql_path = Path("") / "src" / "sql" / "statements.sql"
        data, columns = execute_sql_file(db_path, sql_path)

    df = pd.DataFrame(data, columns=columns)
    df["StartDate"] = pd.to_datetime(df["StartDate"])
    df["EndDate"] = pd.to_datetime(df["EndDate"])
    return df


def format_columns(value):
    result = str(value)
    if result == "True":
        result = '<div class="True">{}</div>'.format(value)
    if result == "False":
        result = '<div class="False">{}</div>'.format(value)


def conditional_formatting(val):
    """
    Conditional formatting for DataFrame exported as HTML table.
    """
    if val == True:
        return "background-color: rgb(140,225,140)"
    elif val == False:
        return "background-color: rgb(225,160,160)"
    else:
        return ""


def missing():
    """
    Returns a table showing whether available statements cover the first of each
    month for each account in the database. Makes it easier to spot missing statements.
    """
    df = get_statements()

    # Ignore all but the most recent two years of data
    # start_date = df["EndDate"].max() - timedelta(weeks=104)
    # df = df[df["StartDate"] >= start_date]

    # Construct a table that contains one element for each account for each day
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

    # Make the table beautiful and helpful
    df_transpose = df_pivot.tail(13).T
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning)
        df_styled = (
            df_transpose.style.applymap(conditional_formatting)
            .set_table_attributes("border=1")
            .set_properties(**{"text-align": "center"})
        )

    # Create a temporary html file containing the table.
    # Open the file in default browser, wait 1 sec for it to load, then delete the temp file.
    with NamedTemporaryFile(mode="w+b", delete=False, suffix=".html") as f:
        df_styled.to_html(f.name, index=True)
        name = os.name
        if name == "nt":
            webbrowser.open(f.name)
        elif name == "posix":
            browser = r"open -a /Applications/Google\ Chrome.app %s"
            webbrowser.get(browser).open(f.name)
        else:
            raise ValueError("Unsupported OS type %s" % name)


if __name__ == "__main__":
    missing()
