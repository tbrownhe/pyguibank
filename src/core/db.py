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


def update_db_where(
    db_path: Path,
    table: str,
    update_cols: list[str],
    update_list: list[tuple],
    where_cols: list[str],
    where_list: list[tuple],
):
    """
    Updates rows of data in an sqlite3 data table
    Example:
        table = "Transactions"
        update_cols = ["Category", "Verified"]
        update_list = [("Auto", 1), ("Restaurant", 1)]
        where_cols = ["TranID", "AccountID"]
        where_list = [(1, 6), (42, 6)]
    """
    # Ensure passed data is a uniform array
    assert all([len(update_vals) == len(update_cols) for update_vals in update_list])
    assert all([len(where_vals) == len(where_cols) for where_vals in where_list])

    # Prepare query parts
    table_str = "UPDATE %s" % table
    update_str_list = ["%s='%s'" % (col, "%s") for col in update_cols]
    update_template = "SET " + ", ".join(update_str_list)
    where_str_list = ["%s='%s'" % (col, "%s") for col in where_cols]
    where_template = "WHERE " + " AND ".join(where_str_list)

    # Update all rows in a single commit
    with open_sqlite3(db_path) as cursor:
        for update_vals, where_vals in zip(update_list, where_list):
            # Finalize the query for this row and execute it
            update_str = update_template % update_vals
            where_str = where_template % where_vals
            query = " ".join([table_str, update_str, where_str])
            cursor.execute(query)
