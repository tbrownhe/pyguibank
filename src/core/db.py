import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Any

from loguru import logger
from sqlalchemy.orm import Session
from .orm import BaseModel


@contextmanager
def open_sqlite3(db_path: Path) -> Generator:
    conn = sqlite3.connect(db_path)
    try:
        yield conn.cursor()
    finally:
        conn.commit()
        conn.close()


def create_new_db(db_path: Path):
    sql_path = Path("") / "src/sql/new_db.sql"
    with sql_path.open("r") as f:
        query = f.read()
    with open_sqlite3(db_path) as cursor:
        cursor.executescript(query)


def insert_rows_batched(session: Session, model: BaseModel, rows: list[dict]) -> None:
    """
    Performs batched insertion of rows, rolling back the transaction if any error occurs.

    Args:
        session (Session): SQLAlchemy session object.
        model (Type[Base]): SQLAlchemy model representing the table.
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
    logger.info(
        f"Skipped {skipped} duplicate rows while inserting {n_rows} rows"
        f" into {model.__tablename__}. "
    )


def insert_into_db(
    db_path: Path,
    table: str,
    columns: list[str],
    rows: list[tuple],
    skip_duplicates=False,
) -> None:
    """
    Inserts rows of data into an sqlite3 data table
    """
    # Ensure passed data is a uniform array
    assert all([len(row) == len(columns) for row in rows])

    # Create query string
    columns_str = f"({(','.join(columns))})"
    values_str = f"({(','.join(['?'] * len(columns)))})"
    query = "INSERT INTO %s %s VALUES %s" % (table, columns_str, values_str)

    # Insert data into SQL table
    duplicates = 0
    with open_sqlite3(db_path) as cursor:
        for row in rows:
            try:
                cursor.execute(query, row)
            except sqlite3.IntegrityError as err:
                if skip_duplicates:
                    duplicates += 1
                else:
                    raise sqlite3.IntegrityError(err)

    # Print number of duplicates ignored
    if duplicates > 0:
        logger.debug(
            "Ignored {n} duplicate rows out of {m} total.", n=duplicates, m=len(rows)
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
        model (Base): SQLAlchemy ORM model class representing the table.
        update_cols (List[str]): Columns to update.
        update_list (List[Tuple]): Values to update in the corresponding columns.
        where_cols (List[str]): Columns for the WHERE clause.
        where_list (List[Tuple]): Values for the WHERE clause.
    """
    if len(update_list) != len(where_list):
        raise ValueError("Length of update_list and where_list must be equal.")

    for update_vals, where_vals in zip(update_list, where_list):
        # Build the WHERE clause dynamically
        conditions = {
            getattr(model, col): val for col, val in zip(where_cols, where_vals)
        }

        # Update the rows matching the conditions
        session.query(model).filter_by(**conditions).update(
            {getattr(model, col): val for col, val in zip(update_cols, update_vals)},
            synchronize_session="fetch",  # Ensures in-memory consistency
        )

    session.commit()
