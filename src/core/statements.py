import shutil
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path

from loguru import logger
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QMessageBox, QProgressDialog

from . import query
from .db import insert_into_db
from .dialog import AssignAccountNumber
from .parse import parse_any
from .utils import hash_file, hash_transactions
from .validation import Statement


class StatementProcessor:

    def __init__(self, config: ConfigParser) -> None:
        """Initialize the processor and make sure config is valid

        Args:
            config (ConfigParser): Configuration read from config.ini
        """
        self.config = config
        try:
            self.db_path = Path(self.config.get("DATABASE", "db_path")).resolve()
            self.import_dir = Path(self.config.get("IMPORT", "import_dir")).resolve()
            self.success_dir = Path(self.config.get("IMPORT", "success_dir")).resolve()
            self.duplicate_dir = Path(
                self.config.get("IMPORT", "duplicate_dir")
            ).resolve()
            self.hard_fail = config.getboolean("IMPORT", "hard_fail")
            self.fail_dir = Path(config.get("IMPORT", "fail_dir")).resolve()
            self.extensions = [
                ext.strip()
                for ext in self.config.get("IMPORT", "extensions").split(",")
            ]
        except Exception:
            logger.exception("Failed to load configuration: ")

    def import_all(self, parent=None) -> None:
        """Finds all statements in import_dir and imports all of them.

        Args:
            parent (_type_, optional): Parent class. Defaults to None.
        """
        # Get the list of files in the input_dir
        fpaths = []
        for ext in self.extensions:
            fpaths.extend(self.import_dir.glob("*." + ext))

        # Create progress dialog
        progress = QProgressDialog(
            "Processing statements...", "Cancel", 0, len(fpaths), parent
        )
        progress.setWindowTitle("Import Progress")
        progress.setWindowModality(Qt.WindowModal)
        progress.setValue(0)

        # Import all files
        success = 0
        duplicate = 0
        fail = 0
        for idx, fpath in enumerate(sorted(fpaths)):
            progress.setLabelText(f"Processing {fpath.name}...")
            if progress.wasCanceled():
                QMessageBox.information(
                    parent, "Import Canceled", "The import was canceled."
                )
                break
            try:
                suc, dup = self.import_one(fpath)
                success += suc
                duplicate += dup
            except Exception:
                fail += 1
                logger.exception("Import failed: ")
                if self.hard_fail:
                    raise
                else:
                    dpath = self.fail_dir / fpath.name
                    self.move_file_safely(fpath, dpath)

            # Update progress dialog
            progress.setValue(idx + 1)

        # Show summary
        total = len(fpaths)
        remain = total - success - duplicate - fail
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setText(
            f"Successfully imported {success} of {total} files in {self.import_dir}."
            f"\n{duplicate} duplicate files were found,"
            f"\n{fail} files failed to import, and"
            f"\n{remain} files remain to be imported."
        )
        msg_box.setWindowTitle("Import Summary")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

    def import_one(self, fpath: Path) -> tuple[int, int]:
        """Parses the statement and saves the transaction data to the database.

        Args:
            fpath (Path): Statement file to import

        Returns:
            tuple[int, int]: success, duplicate count
        """
        logger.info("Importing {f}", f=fpath.name)

        # Abort if this exact statement file has already been imported to db
        md5hash = hash_file(fpath)
        if self.file_already_imported(md5hash):
            self.handle_duplicate(fpath)
            return 0, 1

        # Extract the statement data into a Statement dataclass
        self.statement = parse_any(self.db_path, fpath)
        if not isinstance(self.statement, Statement):
            raise TypeError("Parsing module must return a Statement dataclass")

        # Attach metadata
        self.attach_metadata(md5hash)

        # Abort if a statement with similar metadata has been imported
        if self.statement_already_imported(self.statement.dpath.name):
            self.handle_duplicate(fpath)
            return 0, 1

        # Insert statement metadata into db
        self.insert_statement_metadata()

        # Insert transactions into db
        self.insert_statement_data()

        # Rename and move the statement file to the success directory
        self.move_file_safely(self.statement.fpath, self.statement.dpath)
        return 1, 0

    def attach_metadata(self, md5hash: str) -> None:
        # Add the statement file hash
        self.statement.add_md5hash(self.md5hash)

        # Attach the account_id and account_name
        self.attach_account_info()

        # Create a destination path based on the statement metadata
        self.attach_standard_dpath()

    def handle_duplicate(self, fpath):
        dpath = self.duplicate_dir / fpath.name
        self.move_file_safely(fpath, dpath)
        logger.info("Duplicate statement moved to {d}", d=dpath)

    def move_file_safely(self, fpath: Path, dpath: Path):
        """Make sure destination parent dir exists

        Args:
            fpath (Path): Source Path
            dpath (Path): Desintation Path
        """
        dpath.parents[0].mkdir(parents=True, exist_ok=True)

        while True:
            try:
                shutil.move(fpath, dpath)
                return
            except PermissionError:
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setText(
                    f"The statement {fpath.name} could not be moved."
                    " If it's open in another program, please close it and click OK"
                )
                msg_box.setWindowTitle("Unable to Move File")
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.exec_()

    def file_already_imported(self, md5hash: str) -> bool:
        """Check if the file has already been saved to the db

        Args:
            db_path (Path): Path to db
            md5hash (str): Byte hash of passed file

        Returns:
            bool: Whether md56hash exists in the db already
        """
        data = query.statements_containing_hash(self.db_path, md5hash)
        if len(data) == 0:
            return False

        for statement_id, filename in data:
            logger.info(
                f"Previously imported {filename} (StatementID: {statement_id})"
                f" has identical hash {md5hash}"
            )
        return True

    def statement_already_imported(self, filename: Path) -> bool:
        """Check if the file has already been saved to the db

        Args:
            db_path (Path): Path to db
            filename (str): Name of statement file after standardization

        Returns:
            bool: Whether md56hash exists in the db already
        """
        data = query.statements_containing_filename(self.db_path, filename)
        if len(data) == 0:
            return False

        for statement_id, filename in data:
            logger.info(f"Previously imported {filename} (StatementID: {statement_id})")
        return True

    def attach_account_info(self) -> None:
        """
        Makes sure all accounts in the statement have an entry in the lookup table.
        Return the nicknames of all accounts
        """
        # Ensure an account-to-account_num association is set up for each account_num
        for account in self.statement.accounts:
            try:
                # Lookup existing account
                account_id = query.account_id(self.db_path, account.account_num)
            except KeyError:
                # Prompt user to select account to associate with this account_num
                account_id = self.prompt_account_num(account.account_num)

            # Get the account_name for this account_id
            account_name = query.account_name(self.db_path, account.account_id)

            # Add the new data to the account
            account.add_account_info(account_id, account_name)

    def prompt_account_num(self, account_num: str) -> int:
        """
        Ask user to associate this unknown account_num with an Accounts.AccountID
        """
        dialog = AssignAccountNumber(
            self.db_path, self.statement.fpath, self.statement.stid, account_num
        )
        if dialog.exec_() == QDialog.Accepted:
            return dialog.get_account_id()
        raise ValueError("No AccountID selected.")

    def attach_standard_dpath(self) -> None:
        """
        Creates consistent destination path.
        Uses first account as the main account.
        """
        # Validate optional fields that must be present by now
        self.statement.accounts[0].validate_account_info()

        dname = (
            "_".join(
                [
                    self.statement.accounts[0].account_name,
                    self.statement.start_date.strftime(r"%Y-%m-%d"),
                    self.statement.end_date.strftime(r"%Y-%m-%d"),
                ]
            )
            + self.statement.fpath.suffix.lower()
        )
        dpath = self.success_dir / dname
        self.statement.add_dpath(dpath)

    def insert_statement_metadata(self) -> None:
        """Updates db with information about this statement file."""
        for account in self.statement.accounts:
            # Account should have account_id and account_name by now
            account.validate_account_info()

            # Assemble the metadata
            columns = [
                "StatementTypeID",
                "AccountID",
                "ImportDate",
                "StartDate",
                "EndDate",
                "StartBalance",
                "EndBalance",
                "TransactionCount",
                "Filename",
                "MD5",
            ]
            metadata = (
                self.statement.stid,
                account.account_id,
                datetime.now().strftime(r"%Y-%m-%d"),
                self.statement.start_date.strftime(r"%Y-%m-%d"),
                self.statement.end_date.strftime(r"%Y-%m-%d"),
                account.start_balance,
                account.end_balance,
                len(account.transactions),
                self.statement.dpath.name,
                self.statement.md5hash,
            )

            # Insert metadata into db
            insert_into_db(self.db_path, "Statements", columns, [metadata])

            # Get the new StatementID and attach it to account
            statement_id = query.statement_id(
                self.db_path, account.account_id, self.statement.md5hash
            )
            account.add_statement_id(statement_id)

    def insert_statement_data(self) -> None:
        """Convert Statement dataclass to list of tuple for insertion into SQLite"""
        # Save transaction data for each account to the db
        for account in self.statement.accounts:
            # All optional account fields should be populated by now
            account.validate_complete()

            if len(account.transactions) == 0:
                # Skip. There will still be metadata in Statements table
                continue

            # Construct list of tuple containing transaction data
            transactions = []
            for transaction in account.transactions:
                transactions.append(
                    (
                        account.account_id,
                        transaction.posting_date.strftime(r"%Y-%m-%d"),
                        transaction.amount,
                        transaction.balance,
                        transaction.desc,
                    )
                )

            # Hash each transaction
            transactions = hash_transactions(transactions)

            # Prepend the StatementID to each transaction row
            transactions = [(account.statement_id,) + row for row in transactions]

            match account.account_name:
                case "amazonper":
                    self.insert_into_shopping(transactions)
                case "amazonbus":
                    self.insert_into_shopping(transactions)
                case _:
                    self.insert_into_transactions(transactions)

    def insert_into_shopping(self, transactions: list[tuple]) -> None:
        """Insert the transactions into the shopping db table

        Args:
            transactions (list[tuple]): List of transactions ready for insertion
        """
        # Insert rows into database
        columns = [
            "StatementID",
            "AccountID",
            "CardID",
            "OrderID",
            "Date",
            "Amount",
            "Description",
            "MD5",
        ]
        insert_into_db(
            self.db_path, "Shopping", columns, transactions, skip_duplicates=True
        )

    def insert_into_transactions(self, transactions: list[tuple]) -> None:
        """Insert the transactions into the transactions db table

        Args:
            transactions (list[tuple]): List of transactions ready for insertion
        """
        # Insert rows into database
        columns = [
            "StatementID",
            "AccountID",
            "Date",
            "Amount",
            "Balance",
            "Description",
            "MD5",
        ]
        insert_into_db(
            self.db_path, "Transactions", columns, transactions, skip_duplicates=True
        )
