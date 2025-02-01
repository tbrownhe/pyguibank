from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from core.settings import settings


class StatementSubmissionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Secure Statement Submission Form")
        self.setMinimumWidth(600)

        # Layout
        layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel(
            "Please select a bank statement file you need a plugin for"
            " and provide all required details.\n\n"
            "All data is sent using end-to-end encryption over https,"
            " and your file is stored using AES encryption at rest."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Form layout
        form_layout = QFormLayout()

        # File Picker
        self.file_path_input = QLineEdit()
        self.file_path_input.setPlaceholderText("No file selected")
        self.file_path_input.setReadOnly(True)
        self.file_picker_button = QPushButton("Select File")
        self.file_picker_button.clicked.connect(self.pick_file)
        form_layout.addRow("Statement File:", self.file_picker_button)
        form_layout.addRow("Selected File:", self.file_path_input)

        # Institution Name
        self.institution_input = QLineEdit()
        self.institution_input.setPlaceholderText("e.g., Bank of America")
        form_layout.addRow("Institution Name:", self.institution_input)

        # Statement Frequency Dropdown
        self.frequency_input = QComboBox()
        self.frequency_input.addItems(["Daily", "Weekly", "Monthly", "Quarterly", "Annually", "Other"])
        form_layout.addRow("Statement Frequency:", self.frequency_input)

        # User Email
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("your.email@example.com")
        form_layout.addRow("Your Email Address:", self.email_input)

        # Comments (Limited to 256 characters)
        self.comments_input = QTextEdit()
        self.comments_input.setPlaceholderText("Add any notes or clarifications (max 256 characters)...")
        self.comments_input.setMaximumHeight(80)
        form_layout.addRow("Additional Comments:", self.comments_input)

        layout.addLayout(form_layout)

        # Submit & Cancel Buttons
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.submit_data)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        # Add buttons to layout
        layout.addWidget(self.submit_button)
        layout.addWidget(self.cancel_button)

    def pick_file(self):
        """
        Opens a file picker dialog and sets the selected file path.
        """
        default_dir = str(settings.fail_dir)
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Bank Statement",
            default_dir,
            "All Files (*.*);;PDF Files (*.pdf)",
        )
        if file_path:
            self.file_path_input.setText(file_path)

    def submit_data(self):
        """
        Collect user input, validate it, and return the metadata.
        """
        file_path = self.file_path_input.text().strip()
        institution = self.institution_input.text().strip()
        frequency = self.frequency_input.currentText()
        email = self.email_input.text().strip()
        comments = self.comments_input.toPlainText().strip()

        # Validate inputs
        if not file_path:
            QMessageBox.warning(self, "Input Error", "Please select a file.")
            return

        if not institution:
            QMessageBox.warning(self, "Input Error", "Institution name is required.")
            return

        if not email or "@" not in email:
            QMessageBox.warning(self, "Input Error", "Please enter a valid email address.")
            return

        if len(comments) > 256:
            QMessageBox.warning(self, "Input Error", "Comments must be 256 characters or less.")
            return

        # Store result
        self.metadata = {
            "file_path": file_path,
            "institution": institution,
            "frequency": frequency,
            "email": email,
            "comments": comments,
        }

        self.accept()  # Close dialog and return success

    def get_metadata(self):
        """
        Return metadata dictionary after submission.
        """
        return getattr(self, "metadata", None)
