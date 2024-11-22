import itertools
from pathlib import Path

import pandas as pd
from loguru import logger

from .db import update_db_where
from .learn import predict
from .query import transactions

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
    where_cols = ["TransactionID"]
    where_list = list(zip(df["TransactionID"]))
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

    df_db = transactions()
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


def categorize_new(db_path: Path, model_path: Path) -> int:
    """
    Uses the trained classifiation model to categorize any transactions that have
    Category='Uncategorized' or blank.
    """
    # Pull all uncategorized transactions
    where = "WHERE Transactions.Category='Uncategorized' OR Transactions.Category=''"
    data, columns = transactions(db_path, where=where)
    df = pd.DataFrame(data, columns=columns)
    if len(df) == 0:
        print("No new transactions to categorize!")
        return

    # Categorize the transactions
    df = predict(model_path, df)

    # Update the database with the new categories.
    # Set the Verified flag to False to prevent training the model on these results.
    update_db_categories(df, verified=False)


if __name__ == "__main__":
    print("This script is not designed to be run as __main__")
    # categorize_new_transactions()
