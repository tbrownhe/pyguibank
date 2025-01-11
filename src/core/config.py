import configparser
import json
from configparser import ConfigParser
from pathlib import Path

from loguru import logger
from pydantic import BaseModel, ValidationError
from PyQt5.QtWidgets import QMessageBox
from sqlalchemy.orm import Session

from core import orm, query
from core.settings import settings


def read_config() -> ConfigParser:
    """
    Reads the user-configurable configuration file. If it does not exist,
    a default configuration is initialized and saved.

    Returns:
        ConfigParser: The parsed configuration object.
    """
    config = configparser.ConfigParser()
    if settings.config_path.exists():
        try:
            config.read(settings.config_path)
        except Exception as e:
            logger.error(f"Failed to read config file at {settings.config_path}: {e}")
            raise
    else:
        # If config doesn't exist, create a default configuration
        config = default_config()
        try:
            with settings.config_path.open("w") as f:
                config.write(f)
            logger.info(f"Default configuration created at {settings.config_path}")
        except Exception as e:
            logger.error(f"Failed to create config file at {settings.config_path}: {e}")
            raise

    return config


def default_config() -> ConfigParser:
    config = ConfigParser()
    config["DATABASE"] = {
        "db_path": str(Path.home() / "Documents/PyGuiBank/pyguibank.db")
    }
    config["CLASSIFIER"] = {
        "model_path": str(Path("assets/default_pipeline.mdl").resolve())
    }
    config["IMPORT"] = {
        "extensions": "pdf, csv, xlsx",
        "import_dir": str(Path.home() / "Documents" / "PyGuiBank" / "Imports"),
        "success_dir": str(
            Path.home() / "Documents" / "PyGuiBank" / "Imports" / "SUCCESS"
        ),
        "fail_dir": str(Path.home() / "Documents" / "PyGuiBank" / "Imports" / "FAIL"),
        "duplicate_dir": str(
            Path.home() / "Documents" / "PyGuiBank" / "Imports" / "DUPLICATE"
        ),
        "hard_fail": "True",
    }
    config["REPORTS"] = {
        "report_dir": str(Path.home() / "Documents" / "PyGuiBank" / "Reports")
    }
    return config


def export_init_accounts(session: Session):
    accounts = query.accounts_table(session)
    account_numbers = query.account_numbers_table(session)

    data = {"Accounts": accounts, "AccountNumbers": account_numbers}
    with settings.accounts_json.open("w") as f:
        json.dump(data, f, indent=2)

    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Information)
    msg_box.setText("Successfully exported Accounts configuration.")
    msg_box.setWindowTitle("Configuration Saved")
    msg_box.setStandardButtons(QMessageBox.Ok)
    msg_box.exec_()


class Account(BaseModel):
    AccountID: int
    AccountName: str
    AccountTypeID: int
    Company: str
    Description: str
    AppreciationRate: float


class AccountNumber(BaseModel):
    AccountNumberID: int
    AccountID: int
    AccountNumber: str


class AccountConfig(BaseModel):
    Accounts: list[Account]
    AccountNumbers: list[AccountNumber]


def validate_using_model(fpath: Path, model: BaseModel):
    logger.info(f"Validating JSON file: {fpath}")
    with fpath.open("r") as f:
        data = json.load(f)

    try:
        validated_data = model(**data)
        logger.info("Validation successful.")
        return validated_data
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise ValueError(f"Invalid configuration format: {e}")


def import_init_accounts(session: Session, parent=None):
    """Import account configuration, if available"""
    # Try to grab from default location
    fpath = settings.accounts_json
    if not fpath.exists():
        logger.info(
            f"Account metadata file {fpath} could not be found."
            " A blank database will be initialized."
        )
        return

    reply = QMessageBox.question(
        parent,
        "Load Previous Account Metadata?",
        (
            "Account metadata from a previous database was found."
            " Do you want to initialize the new database with it?\n\n"
            "Click Yes if you want to load previous account names and"
            " account numbers into the new database."
        ),
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )
    if reply == QMessageBox.No:
        QMessageBox.information(
            parent,
            f"Database Without Account Info",
            "Database will be initialized without account information.",
        )
        return

    # Import and validate data
    try:
        validated_data = validate_using_model(fpath, AccountConfig)
    except Exception as e:
        logger.error(f"Validation error: {e}")
        raise

    QMessageBox.information(
        parent,
        f"Database With Account Info",
        "Database will be initialized with previous account information.",
    )

    # Convert Pydantic models to dicts for database insertion
    accounts = [item.dict() for item in validated_data.Accounts]
    account_numbers = [item.dict() for item in validated_data.AccountNumbers]

    # Load into new database
    query.insert_rows_batched(
        session,
        orm.Accounts,
        accounts,
    )
    query.insert_rows_batched(
        session,
        orm.AccountNumbers,
        account_numbers,
    )
