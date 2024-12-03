import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from loguru import logger


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


def get_table_names(db_path: Path, table: str):
    with open_sqlite3(db_path) as cursor:
        result = cursor.execute('SELECT * FROM sqlite_master WHERE type= "table"')
        tables = result.fetchall()
    table_names = []
    for table in tables:
        name = table[1]
        table_names.append(name)
    return table_names


def execute_sql_query(db_path: Path, query: str):
    with open_sqlite3(db_path) as cursor:
        cursor.execute(query)
        data = cursor.fetchall()
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
        else:
            columns = []
    return data, columns


def get_sqltable(db_path: Path, table: str):
    query = "SELECT * FROM %s" % table
    data, columns = execute_sql_query(db_path, query)
    return data, columns


def execute_sql_file(db_path: Path, sql_path: Path):
    with sql_path.open("r") as f:
        query = f.read()
    data, columns = execute_sql_query(db_path, query)
    return data, columns


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


def construct_update_query(
    table: str, update_cols: list[str], where_cols: list[str]
) -> str:
    """
    Constructs an SQL update query with placeholders for values.

    Args:
        table (str): The name of the table to update.
        update_cols (List[str]): Columns to update.
        where_cols (List[str]): Columns for the WHERE clause.

    Returns:
        str: The constructed SQL query with placeholders.
    """
    update_str = ", ".join([f"{col} = ?" for col in update_cols])
    where_str = " AND ".join([f"{col} = ?" for col in where_cols])
    return f"UPDATE {table} SET {update_str} WHERE {where_str}"


def update_db_where(
    db_path: Path,
    table: str,
    update_cols: list[str],
    update_list: list[tuple],
    where_cols: list[str],
    where_list: list[tuple],
) -> None:
    """
    Updates rows of data in an SQLite3 database table.

    Args:
        db_path (Path): Path to the SQLite database file.
        table (str): Name of the table to update.
        update_cols (List[str]): Columns to update.
        update_list (List[Tuple]): Values to update in the corresponding columns.
        where_cols (List[str]): Columns for the WHERE clause.
        where_list (List[Tuple]): Values for the WHERE clause.

    Example:
        table = "Transactions"
        update_cols = ["Category", "Verified"]
        update_list = [("Auto", 1), ("Restaurant", 1)]
        where_cols = ["TransactionID", "AccountID"]
        where_list = [(1, 6), (42, 6)]
    """
    # Ensure data integrity
    if len(update_list) != len(where_list):
        raise ValueError("Length of update_list and where_list must be equal.")
    if any(len(row) != len(update_cols) for row in update_list):
        raise ValueError(
            "Each tuple in update_list must match the number of update_cols."
        )
    if any(len(row) != len(where_cols) for row in where_list):
        raise ValueError(
            "Each tuple in where_list must match the number of where_cols."
        )

    # Construct the base query
    query = construct_update_query(table, update_cols, where_cols)

    # Execute updates
    try:
        with open_sqlite3(db_path) as cursor:
            for update_vals, where_vals in zip(update_list, where_list):
                cursor.execute(query, update_vals + where_vals)
    except sqlite3.Error as e:
        raise RuntimeError(f"Database update failed: {e}")
