from pathlib import Path

from core.db import execute_sql_query

db_path = Path("") / "pyguibank_good.db"
data, _ = execute_sql_query(
    db_path, "SELECT Company, Type, Extension, SearchString, Parser FROM StatementTypes"
)

for i, row in enumerate(data):
    if i + 1 < len(data):
        print(str(row) + ",")
    else:
        print(str(row) + ";")
