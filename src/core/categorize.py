# -*- coding: utf-8 -*-
import itertools
from pathlib import Path

import pandas as pd
from .db import execute_sql_file, execute_sql_query, update_db_where
from .learn import predict, train
from loguru import logger

"""
Contains functions used to categorize transactions.
"""


def transactions_from_csv(csv_path: Path, required_cols: list[str]) -> pd.DataFrame:
    """
    Loads transactions from a csv file and ensures required columns are present.
    """
    logger.info("Loading transactions from csv file.")
    df = pd.read_csv(csv_path)

    # File must contain required columns.
    if not all([col in df.columns for col in required_cols]):
        raise ValueError(
            "%s does not contain all required columns %s."
            % (csv_path.name, required_cols)
        )

    # Drop any rows with missing data in any of the required columns.
    df = df.dropna(axis=0, subset=required_cols)

    return df


def transactions_from_db(where=None) -> pd.DataFrame:
    """
    Returns all transactions in the database as DataFrame.
    """
    logger.info("Retrieving transactions from database.")
    db_path = Path("") / "pyguibank.db"
    if where:
        sql_path = Path("") / "src" / "sql" / "transactions_where.sql"
        with sql_path.open("r") as f:
            query = f.read()
        query = query % where
        data, columns = execute_sql_query(db_path, query)
    else:
        sql_path = Path("") / "src" / "sql" / "transactions_all.sql"
        data, columns = execute_sql_file(db_path, sql_path)
    df = pd.DataFrame(data, columns=columns)
    return df


def update_db_categories(df: pd.DataFrame, verified=False) -> None:
    """
    Updates the db Transactions.Category column with new categories
    from the df.Category column.
    """
    logger.info("Updating database Transactions.Category column.")
    db_path = Path("") / "pyguibank.db"
    update_cols = ["Category", "Verified"]
    value = 1 if verified else 0
    update_list = list(zip(df["Category"], itertools.repeat(value)))
    where_cols = ["TranID"]
    where_list = list(zip(df["TranID"]))
    update_db_where(
        db_path, "Transactions", update_cols, update_list, where_cols, where_list
    )


def update_db_from_csv(fpath: Path) -> None:
    """
    Opens a user-provided .csv file that contains TranID and Category and
    updates the db with the category values.
    """
    df = transactions_from_csv(fpath, ["TranID", "Description", "Category"])

    # Find the transactions where the csv contains a category update
    df_csv = df[["TranID", "Description", "Category"]]
    df_csv = df_csv.rename(columns={"Category": "Category_csv"})

    df_db = transactions_from_db()
    df_db = df_db.rename(columns={"Category": "Category_db"})

    df_merge = df_db[["TranID", "Description", "Category_db"]].merge(
        df_csv[["TranID", "Category_csv"]], how="inner", on="TranID"
    )
    df_update = df_merge[df_merge["Category_csv"] != df_merge["Category_db"]]

    print("List of transactions where database category disagrees with the csv:")
    print(df_update)

    # Give the user an opportunity to abort
    msg = (
        "The csv contains %s transactions and %s category updates.\n"
        "The database Transaction Category and Verified columns will be updated."
    ) % (len(df), len(df_update))
    print(msg)
    while True:
        match input("Are you sure? y/n: ").lower():
            case "y":
                # Update categories and set Verified=1 since these were reviewed.
                update_db_categories(df, verified=True)
            case "n":
                return
            case _:
                continue


def train_classifier() -> None:
    """
    Pulls all transaction data with verified categorization
    and uses it to train the ML model.
    """
    # Pull all category verified transactions
    df = transactions_from_db(where="Verified=1")
    if len(df) == 0:
        raise ValueError(
            "No verified transactions available to train classifier model."
        )

    # Train with a fraction of the data and test the classification accuracy.
    train(df, test=True)

    # Train with entire data set and save the model.
    print("The classification model will be retrained with the entire dataset.")
    while True:
        match input("Are you sure? y/n: ").lower():
            case "y":
                train(df, test=False)
                return
            case "n":
                return
            case _:
                continue


def categorize_new_transactions() -> None:
    """
    Uses the trained classifiation model to categorize any transactions that have
    Category='Uncategorized' or blank.
    """
    # Pull all uncategorized transactions
    df = transactions_from_db(where="Category='Uncategorized' OR Category=''")
    if len(df) == 0:
        print("No new transactions to categorize!")
        return

    # Categorize the transactions
    df = predict(df)

    # Update the database with the new categories.
    # Set the Verified flag to 0 to prevent training the model on these results.
    update_db_categories(df, verified=False)


if __name__ == "__main__":
    print("This script is not designed to be run as __main__")
    # categorize_new_transactions()
