import shutil
from configparser import ConfigParser
from pathlib import Path

from loguru import logger
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QMessageBox, QProgressDialog
from sqlalchemy.orm import Session, sessionmaker

from . import query
from .dialog import AssignAccountNumber
from .orm import Statements, Transactions
from .parse import parse_any
from .utils import hash_file
from .validation import Statement, Transaction


class StatementProcessor:

    def __init__(self, Session: sessionmaker, config: ConfigParser) -> None:
        """Initialize the processor and make sure config is valid

        Args:
            config (ConfigParser): Configuration read from config.ini
        """
        self.Session = Session
        self.config = config
        try:
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
            except Exception as e:
                fail += 1
                logger.exception("Import failed: ")
                if self.hard_fail:
                    progress.close()
                    msg_box = QMessageBox()
                    msg_box.setIcon(QMessageBox.Critical)
                    msg_box.setText(f"The statement could not be parsed:\n{e}")
                    msg_box.setWindowTitle("Parsing Failed")
                    msg_box.setStandardButtons(QMessageBox.Ok)
                    msg_box.exec_()
                    raise
                else:
                    dpath = self.fail_dir / fpath.name
                    self.move_file_safely(fpath, dpath)

            # Update progress dialog
            progress.setValue(idx + 1)

        progress.close()

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
            tuple[int, int]: success, duplicate, fail count
        """
        logger.info("Importing {f}", f=fpath.name)

        # Abort if this exact statement file has already been imported to db
        md5hash = hash_file(fpath)
        if self.file_already_imported(md5hash):
            self.handle_duplicate(fpath)
            return 0, 1

        # Extract the statement data into a Statement dataclass
        self.statement = parse_any(self.Session, fpath)

        if not isinstance(self.statement, Statement):
            raise TypeError("Parsing module must return a Statement dataclass")

        # Attach metadata
        self.statement.add_md5hash(md5hash)
        self.attach_account_info()
        for account in self.statement.accounts:
            account.hash_transactions()
        self.statement.set_standard_dpath(self.success_dir)

        # Abort if a statement with similar metadata has been imported
        if self.statement_already_imported(self.statement.dpath.name):
            self.handle_duplicate(fpath)
            return 0, 1

        # Insert transactions into db
        with self.Session() as session:
            self.insert_statement_data(session)

        # Rename and move the statement file to the success directory
        self.move_file_safely(self.statement.fpath, self.statement.dpath)

        return 1, 0

    def file_already_imported(self, md5hash: str) -> bool:
        """Check if the file has already been saved to the db

        Args:
            md5hash (str): Byte hash of passed file

        Returns:
            bool: Whether md5hash exists in the db already
        """
        with self.Session() as session:
            data = query.statements_with_hash(session, md5hash)
        if len(data) == 0:
            return False

        for statement_id, filename in data:
            logger.debug(
                f"Previously imported {filename} (StatementID: {statement_id})"
                f" has identical hash {md5hash}"
            )
        return True

    def statement_already_imported(self, filename: Path) -> bool:
        """Check if the file has already been saved to the db

        Args:
            filename (str): Name of statement file after standardization

        Returns:
            bool: Whether md56hash exists in the db already
        """
        with self.Session() as session:
            data = query.statements_with_filename(session, filename)
        if len(data) == 0:
            return False

        for statement_id, filename in data:
            logger.debug(
                f"Previously imported {filename} (StatementID: {statement_id})"
            )
        return True

    def handle_duplicate(self, fpath):
        dpath = self.duplicate_dir / fpath.name
        self.move_file_safely(fpath, dpath)
        logger.debug("Duplicate statement moved to {d}", d=dpath)

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
            except PermissionError as e:
                # File is likely open in another program
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setText(
                    f"The file {fpath.name} could not be moved. "
                    "It might be open in another program. Please close it and try again."
                )
                msg_box.setWindowTitle("Unable to Move File")
                msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

                response = msg_box.exec_()

                if response == QMessageBox.Cancel:
                    raise RuntimeError(
                        f"File move operation for {fpath} was cancelled by the user."
                    ) from e
            except Exception as e:
                # Handle other exceptions gracefully
                raise RuntimeError(
                    f"An unexpected error occurred while moving {fpath}: {e}"
                ) from e

    def attach_account_info(self) -> None:
        """
        Makes sure all accounts in the statement have an entry in the lookup table.
        Return the nicknames of all accounts
        """
        # Ensure an account-to-account_num association is set up for each account_num
        for account in self.statement.accounts:
            try:
                # Lookup existing account
                with self.Session() as session:
                    account_id = query.account_id_of_account_number(
                        session, account.account_num
                    )
            except KeyError:
                # Prompt user to select account to associate with this account_num
                account_id = self.prompt_account_num(account.account_num)

            # Get the account_name for this account_id
            with self.Session() as session:
                account_name = query.account_name_of_account_id(session, account_id)

            # Add the new data to the account
            account.add_account_info(account_id, account_name)

    def prompt_account_num(self, account_num: str) -> int:
        """
        Ask user to associate this unknown account_num with an Accounts.AccountID
        """
        dialog = AssignAccountNumber(
            self.Session, self.statement.fpath, self.statement.stid, account_num
        )
        if dialog.exec_() == QDialog.Accepted:
            return dialog.get_account_id()
        raise ValueError("No AccountID selected.")

    def insert_statement_data(self, session: Session) -> None:
        """
        Inserts statement metadata and associated transactions into the database.
        Rolls back the entire operation if any error occurs.

        Args:
            session (Session): session instance
        """
        with session.begin():
            for account in self.statement.accounts:
                # Validate account information
                if not account.account_id or not account.account_name:
                    raise ValueError(
                        f"Account {account.account_num} must have"
                        " account_id and account_name set."
                    )

                # Prepare and insert statement metadata
                metadata = self.statement.to_db_row(account)
                statement = Statements(**metadata)
                session.add(statement)

                # Flush to get autogenerated StatementID
                session.flush()
                statement_id = statement.StatementID

                # Prepare transactions for insertion
                transactions = Transaction.to_db_rows(
                    statement_id, account.account_id, account.transactions
                )

                # Insert transactions using insert_rows_carefully
                query.insert_rows_carefully(
                    session, Transactions, transactions, skip_duplicates=True
                )
