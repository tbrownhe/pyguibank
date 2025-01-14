from pathlib import Path

from loguru import logger
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.config import default_config, read_config
from core.settings import settings
from core.utils import create_directory


class PreferencesDialog(QDialog):
    def __init__(self, defaults=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setWindowModality(Qt.ApplicationModal)

        # Main layout
        main_layout = QVBoxLayout(self)

        # Create grid layout for form fields
        grid_layout = QGridLayout()
        main_layout.addLayout(grid_layout)

        row = 0
        # DATABASE section
        grid_layout.addWidget(QLabel("Database Path:"), row, 0)
        self.db_path_edit = QLineEdit()
        grid_layout.addWidget(self.db_path_edit, row, 1)
        db_path_button = QPushButton("Select...")
        db_path_button.clicked.connect(self.select_db_path)
        grid_layout.addWidget(db_path_button, row, 2)
        row += 1

        # CLASSIFIER section
        grid_layout.addWidget(QLabel("Classifier Path:"), row, 0)
        self.model_path_edit = QLineEdit()
        grid_layout.addWidget(self.model_path_edit, row, 1)
        model_path_button = QPushButton("Select...")
        model_path_button.clicked.connect(self.select_mdl_path)
        grid_layout.addWidget(model_path_button, row, 2)
        row += 1

        # IMPORT section
        grid_layout.addWidget(QLabel("Import Extensions:"), row, 0)
        self.extensions_edit = QLineEdit()
        grid_layout.addWidget(self.extensions_edit, row, 1)
        row += 1

        grid_layout.addWidget(QLabel("Import Directory:"), row, 0)
        self.import_dir_edit = QLineEdit()
        grid_layout.addWidget(self.import_dir_edit, row, 1)
        import_dir_button = QPushButton("Select...")
        import_dir_button.clicked.connect(
            lambda: self.select_folder(self.import_dir_edit)
        )
        grid_layout.addWidget(import_dir_button, row, 2)
        row += 1

        grid_layout.addWidget(QLabel("Success Directory:"), row, 0)
        self.success_dir_edit = QLineEdit()
        grid_layout.addWidget(self.success_dir_edit, row, 1)
        success_dir_button = QPushButton("Select...")
        success_dir_button.clicked.connect(
            lambda: self.select_folder(self.success_dir_edit)
        )
        grid_layout.addWidget(success_dir_button, row, 2)
        row += 1

        grid_layout.addWidget(QLabel("Fail Directory:"), row, 0)
        self.fail_dir_edit = QLineEdit()
        grid_layout.addWidget(self.fail_dir_edit, row, 1)
        fail_dir_button = QPushButton("Select...")
        fail_dir_button.clicked.connect(lambda: self.select_folder(self.fail_dir_edit))
        grid_layout.addWidget(fail_dir_button, row, 2)
        row += 1

        grid_layout.addWidget(QLabel("Duplicate Directory:"), row, 0)
        self.duplicate_dir_edit = QLineEdit()
        grid_layout.addWidget(self.duplicate_dir_edit, row, 1)
        duplicate_dir_button = QPushButton("Select...")
        duplicate_dir_button.clicked.connect(
            lambda: self.select_folder(self.duplicate_dir_edit)
        )
        grid_layout.addWidget(duplicate_dir_button, row, 2)
        row += 1

        grid_layout.addWidget(QLabel("Hard Fail:"), row, 0)
        self.hard_fail_checkbox = QCheckBox()
        grid_layout.addWidget(self.hard_fail_checkbox, row, 1)
        row += 1

        # REPORTS section
        grid_layout.addWidget(QLabel("Report Directory:"), row, 0)
        self.report_dir_edit = QLineEdit()
        grid_layout.addWidget(self.report_dir_edit, row, 1)
        report_dir_button = QPushButton("Select...")
        report_dir_button.clicked.connect(
            lambda: self.select_folder(self.report_dir_edit)
        )
        grid_layout.addWidget(report_dir_button, row, 2)
        row += 1

        # Buttons
        button_layout = QHBoxLayout()
        main_layout.addLayout(button_layout)

        load_defaults_button = QPushButton("Restore Defaults")
        load_defaults_button.clicked.connect(self.load_defaults)
        button_layout.addWidget(load_defaults_button)

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_preferences)
        button_layout.addWidget(save_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        # Set the window size
        hint = main_layout.sizeHint()
        self.setFixedSize(2 * hint.width(), hint.height())

        # Populate the fields with the config
        self.config = default_config() if defaults else read_config()
        self.populate_fields()

    def populate_fields(self):
        self.db_path_edit.setText(self.config.get("DATABASE", "db_path"))
        self.model_path_edit.setText(self.config.get("CLASSIFIER", "model_path"))
        self.extensions_edit.setText(self.config.get("IMPORT", "extensions"))
        self.import_dir_edit.setText(self.config.get("IMPORT", "import_dir"))
        self.success_dir_edit.setText(self.config.get("IMPORT", "success_dir"))
        self.fail_dir_edit.setText(self.config.get("IMPORT", "fail_dir"))
        self.duplicate_dir_edit.setText(self.config.get("IMPORT", "duplicate_dir"))
        self.hard_fail_checkbox.setChecked(
            self.config.getboolean("IMPORT", "hard_fail")
        )
        self.report_dir_edit.setText(self.config.get("REPORTS", "report_dir"))

    def load_defaults(self):
        """
        Load the default configuration values into the fields.
        """
        self.config = default_config()
        self.populate_fields()

    def select_db_path(self):
        self.select_path(self.db_path_edit, "Database Files (*.db)")

    def select_mdl_path(self):
        self.select_path(self.model_path_edit, "Model Files (*.mdl)")

    def select_path(self, line_edit, ftype: str):
        """Select a path"""
        try:
            default_path = str(Path(line_edit.text()).resolve())
        except:
            default_path = ""
        fpath, _ = QFileDialog.getOpenFileName(
            self,
            "Select File",
            default_path,
            f"{ftype};;All Files (*)",
        )
        if fpath:
            fpath = Path(fpath).resolve()
            line_edit.setText(str(fpath))

    def select_folder(self, line_edit):
        """Select a folder and set its path in the specified QLineEdit."""
        try:
            default_path = str(Path(line_edit.text()).resolve())
        except:
            default_path = ""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder", default_path
        )
        if folder_path:
            folder_path = Path(folder_path).resolve()
            line_edit.setText(str(folder_path))

    def save_preferences(self):
        """Save the preferences to the configuration file."""
        # Confirmation dialog
        reply = QMessageBox.question(
            self,
            "Confirm Save",
            "Are you sure you want to save the setup?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.No:
            return

        # Store settings in config object
        self.config.set("DATABASE", "db_path", self.db_path_edit.text())
        self.config.set("CLASSIFIER", "model_path", self.model_path_edit.text())
        self.config.set("IMPORT", "extensions", self.extensions_edit.text())
        self.config.set("IMPORT", "import_dir", self.import_dir_edit.text())
        self.config.set("IMPORT", "success_dir", self.success_dir_edit.text())
        self.config.set("IMPORT", "fail_dir", self.fail_dir_edit.text())
        self.config.set("IMPORT", "duplicate_dir", self.duplicate_dir_edit.text())
        self.config.set("IMPORT", "hard_fail", str(self.hard_fail_checkbox.isChecked()))
        self.config.set("REPORTS", "report_dir", self.report_dir_edit.text())

        # Create directories
        create_directory(Path(self.config.get("DATABASE", "db_path")).parent)
        create_directory(Path(self.config.get("IMPORT", "import_dir")))
        create_directory(Path(self.config.get("IMPORT", "success_dir")))
        create_directory(Path(self.config.get("IMPORT", "fail_dir")))
        create_directory(Path(self.config.get("IMPORT", "duplicate_dir")))
        create_directory(Path(self.config.get("REPORTS", "report_dir")))

        # Write config to file
        create_directory(settings.config_path.parent)
        try:
            with settings.config_path.open("w") as config_file:
                self.config.write(config_file)
            logger.info(f"Configuration file created at {settings.config_path}")
        except OSError as e:
            logger.error(f"Error creating configuration file: {e}")
            raise

        # Confirm to user and close dialog
        QMessageBox.information(
            self, "Preferences Saved", "Preferences have been saved successfully."
        )
        self.accept()

    def reject(self):
        reply = QMessageBox.question(
            self,
            "Confirm Exit",
            "Are you sure you want to cancel setup?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            super().reject()
