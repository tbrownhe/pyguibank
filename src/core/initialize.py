from loguru import logger
from PyQt5.QtWidgets import QMessageBox
from sqlalchemy.orm import sessionmaker

from core import orm
from core.config import import_init_accounts
from core.query import insert_rows_batched, optimize_db
from core.settings import settings
from core.utils import create_directory

# Define AccountTypes table
ACCOUNT_TYPES = [
    {"AccountTypeID": 1, "AccountType": "Checking", "AssetType": "Asset"},
    {"AccountTypeID": 2, "AccountType": "Savings", "AssetType": "Asset"},
    {"AccountTypeID": 3, "AccountType": "Credit Card", "AssetType": "Debt"},
    {"AccountTypeID": 4, "AccountType": "401k", "AssetType": "Asset"},
    {"AccountTypeID": 5, "AccountType": "HSA", "AssetType": "Asset"},
    {"AccountTypeID": 6, "AccountType": "Loan", "AssetType": "Debt"},
    {"AccountTypeID": 7, "AccountType": "Shopping", "AssetType": "Spending"},
    {
        "AccountTypeID": 8,
        "AccountType": "TangibleAsset",
        "AssetType": "TangibleAsset",
    },
]


def initialize_dirs() -> None:
    """Ensure all required dirs in settings exist."""
    create_directory(settings.db_path.parent)
    create_directory(settings.import_dir)
    create_directory(settings.success_dir)
    create_directory(settings.fail_dir)
    create_directory(settings.duplicate_dir)
    create_directory(settings.report_dir)


def initialize_db(parent=None) -> sessionmaker:
    """Ensure db file exists and return sessionmaker.

    Args:
        parent (optional): GUI instance that called this function. Defaults to None.

    Returns:
        sessionmaker: Database Session maker
    """
    print("here", settings.db_path)
    if settings.db_path.exists():
        # Connect to and clean up the existing db
        Session = orm.create_database(settings.db_path)
        with Session() as session:
            optimize_db(session)
        logger.info(f"Connected to database at {settings.db_path}")
        return Session
    else:
        # Initialize a new db and import any saved account metadata
        create_directory(settings.db_path.parent)
        Session = orm.create_database(settings.db_path)
        QMessageBox.information(
            parent,
            "New Database Created",
            f"Initialized new database at <pre>{settings.db_path}</pre>",
        )

        # Initialize AccountTypes and Accounts
        with Session() as session:
            insert_rows_batched(
                session,
                orm.AccountTypes,
                ACCOUNT_TYPES,
            )
            import_init_accounts(session)

        logger.info(f"Initialized new database at {settings.db_path}")
        return Session
