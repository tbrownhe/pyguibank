import sqlite3
from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from .orm import BaseModel


def insert_rows_batched(session: Session, model: BaseModel, rows: list[dict]) -> None:
    """
    Performs batched insertion of rows, rolling back the transaction if any error occurs.

    Args:
        session (Session): SQLAlchemy session object.
        model (BaseModel): SQLAlchemy model representing the table.
        rows (list[dict]): List of dictionaries representing rows to insert.

    Raises:
        IntegrityError: If the insertion fails, the entire batch is rolled back.
    """
    try:
        objects = [model(**row) for row in rows]
        session.bulk_save_objects(objects)
        session.commit()
    except sqlite3.IntegrityError as e:
        session.rollback()
        raise RuntimeError(f"Batch insertion failed: {e}")


def insert_rows_carefully(
    session: Session,
    model: BaseModel,
    data: list[dict[str, Any]],
    skip_duplicates: bool = False,
) -> None:
    """
    Insert rows into the database one by one, with optional duplicate handling.

    Args:
        session (Session): SQLAlchemy session.
        model (Type[Base]): SQLAlchemy ORM model for the target table.
        data (List[Dict[str, Any]]): List of data rows to insert as dictionaries.
        skip_duplicates (bool): Whether to skip duplicate rows.

    Returns:
        None
    """
    # Initialize counters
    skipped = 0
    n_rows = len(data)

    for row in data:
        try:
            session.add(model(**row))
            session.commit()
        except sqlite3.IntegrityError:
            # Rollback the failed transaction
            session.rollback()
            if skip_duplicates:
                skipped += 1
            else:
                # Re-raise if not skipping duplicates
                raise

    # Summary message
    if skipped > 0:
        logger.info(
            f"Skipped {skipped} duplicate rows while inserting {n_rows} rows"
            f" into {model.__tablename__}. "
        )


def update_db_where(
    session: Session,
    model: BaseModel,
    update_cols: list[str],
    update_list: list[tuple],
    where_cols: list[str],
    where_list: list[tuple],
) -> None:
    """
    Updates rows of data in an SQLAlchemy-managed database table.

    Args:
        session (Session): SQLAlchemy session object.
        model (BaseModel): SQLAlchemy ORM model class representing the table.
        update_cols (list[str]): Columns to update.
        update_list (list[tuple]): Values to update in the corresponding columns.
        where_cols (list[str]): Columns for the WHERE clause.
        where_list (list[tuple]): Values for the WHERE clause.
    """
    if len(update_list) != len(where_list):
        raise ValueError("Length of update_list and where_list must be equal.")

    for update_vals, where_vals in zip(update_list, where_list):
        # Build the WHERE clause dynamically
        conditions = [
            getattr(model, col) == val for col, val in zip(where_cols, where_vals)
        ]

        # Update the rows matching the conditions
        session.query(model).filter(*conditions).update(
            {getattr(model, col): val for col, val in zip(update_cols, update_vals)},
            synchronize_session="fetch",  # Ensures in-memory consistency
        )

    session.commit()
