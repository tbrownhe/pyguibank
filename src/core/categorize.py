import itertools
from pathlib import Path

import pandas as pd
from loguru import logger

from .db import update_db_where
from .learn import predict
from .query import training_set


def update_db_categories(db_path: Path, df: pd.DataFrame) -> None:
    """
    Updates the db Transactions.Category column with new categories
    from the df.Category column.
    """
    logger.info("Updating database Transactions.Category column.")
    update_cols = ["Category", "ConfidenceScore"]
    update_list = list(zip(df["Category"], df["ConfidenceScore"]))
    where_cols = ["TransactionID"]
    where_list = list(zip(df["TransactionID"]))
    update_db_where(
        db_path, "Transactions", update_cols, update_list, where_cols, where_list
    )


def categorize_transactions(
    db_path: Path, model_path: Path, where: str
) -> pd.DataFrame:
    """
    Uses the trained classifiation model to categorize transactions where...
    """
    data, columns = training_set(db_path, where=where)
    if len(data) == 0:
        print("No new transactions to categorize!")
        return

    # Categorize the transactions
    df = pd.DataFrame(data, columns=columns)
    df = predict(model_path, df)
    return df


def categorize_uncategorized(db_path: Path, model_path: Path):
    where = "WHERE Category = 'Uncategorized' OR Category = '' OR Category IS NULL"
    df = categorize_transactions(db_path, model_path, where)
    update_db_categories(db_path, df)


def categorize_unverified(db_path: Path, model_path: Path):
    where = "WHERE Verified != 1"
    df = categorize_transactions(db_path, model_path, where)
    update_db_categories(db_path, df)
