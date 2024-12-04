from pathlib import Path

import pandas as pd
from loguru import logger
from sqlalchemy.orm import Session

from .orm import Transactions
from .db import update_db_where
from .learn import predict
from .query import training_set


def update_db_categories(session: Session, df: pd.DataFrame) -> None:
    """
    Updates the database's Transactions table with new categories and confidence scores.

    Args:
        session (Session): SQLAlchemy session object.
        df (pd.DataFrame): DataFrame containing TransactionID, Category, and ConfidenceScore.
    """
    logger.info("Updating database Transactions.Category column.")

    # Prepare the update and where data
    update_cols = ["Category", "ConfidenceScore"]
    update_list = list(zip(df["Category"], df["ConfidenceScore"]))
    where_cols = ["TransactionID"]
    where_list = list(zip(df["TransactionID"]))

    # Use the generalized update function
    update_db_where(
        session, Transactions, update_cols, update_list, where_cols, where_list
    )


def categorize_transactions(
    session: Session,
    model_path: Path,
    unverified: bool = True,
    uncategorized: bool = True,
) -> None:
    """
    Categorize transactions based on specified flags and update the database.

    Args:
        session (Session): SQLAlchemy session object.
        model_path (Path): Path to the trained classification model.
        unverified (bool, optional): Categorize only unverified transactions if True.
        uncategorized (bool, optional): Categorize only uncategorized transactions if True.
    """
    # Fetch the transactions based on the flags
    data, columns = training_set(
        session, unverified=unverified, uncategorized=uncategorized
    )

    if len(data) == 0:
        print("No new transactions to categorize!")
        return

    # Convert to DataFrame for processing
    df = pd.DataFrame(data, columns=columns)

    # Categorize the transactions using the model
    df = predict(model_path, df)

    # Update the categorized transactions in the database
    update_db_categories(session, df)
