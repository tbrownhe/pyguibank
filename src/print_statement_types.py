from pathlib import Path

from core.db import execute_sql_query

db_path = Path("") / "pyguibank.db"
data, _ = execute_sql_query(
    db_path,
    "SELECT AccountTypeID, Company, Description, Extension, SearchString, Parser, EntryPoint FROM StatementTypes",
)

for i, row in enumerate(data):
    if i + 1 < len(data):
        print(str(row) + ",")
    else:
        print(str(row) + ";")
