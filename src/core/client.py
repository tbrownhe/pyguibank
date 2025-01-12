import os
from pathlib import Path

import requests
from loguru import logger
from packaging import version
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMessageBox, QProgressDialog

from core.settings import settings
from core.utils import open_file_in_os


def get_download_dir() -> Path:
    """
    Get the platform-specific downloads directory.

    Returns:
        Path: The downloads directory for the current platform.
    """
    name = os.name
    if name == "nt":  # Windows
        return Path(os.getenv("USERPROFILE")) / "Downloads"
    elif name == "posix":
        home_dir = Path.home()
        if "XDG_DOWNLOAD_DIR" in os.environ:  # Linux with XDG spec
            return Path(os.getenv("XDG_DOWNLOAD_DIR"))
        return home_dir / "Downloads"  # Default for Linux/macOS
    else:
        raise ValueError("Unsupported operating system")


def get_client_installers():
    """
    Fetch the list of available client installers from the server.

    Returns:
        list[dict]: A list of client installer metadata.
    """
    try:
        response = requests.get(f"{settings.server_url}/clients")
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()  # Parse JSON response
    except requests.RequestException as e:
        print(f"Error fetching client installers: {e}")
        return []


def is_newer_version(local_version, server_version):
    """
    Compare local and server versions.

    Args:
        local_version (str): The current local version.
        server_version (str): The version available on the server.

    Returns:
        bool: True if the server version is newer, False otherwise.
    """
    return version.parse(server_version) > version.parse(local_version)


def download_client_installer(installer_metadata, progress_dialog=None):
    """
    Download the specified client installer.

    Args:
        installer_metadata (dict): Metadata of the installer to download.
    """
    filename = installer_metadata["file_name"]
    platform = installer_metadata["platform"]
    version = installer_metadata["version"]
    url = f"{settings.server_url}/clients/{platform}/{version}"
    save_path = get_download_dir() / filename
    save_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        # Get total file size from headers
        total_size = int(response.headers.get("content-length", 0))
        chunk_size = 8192  # 8 KB

        if progress_dialog:
            progress_dialog.setMaximum(total_size)
            progress_dialog.setValue(0)

        # Write to file in chunks
        with save_path.open("wb") as f:
            downloaded_size = 0
            for chunk in response.iter_content(chunk_size):
                f.write(chunk)
                downloaded_size += len(chunk)

                # Update progress bar
                if progress_dialog:
                    progress_dialog.setValue(downloaded_size)
                    if progress_dialog.wasCanceled():
                        raise RuntimeError("Download canceled by the user")

        logger.success(f"Downloaded installer to {save_path}")
        return save_path
    except requests.RequestException as e:
        logger.error(f"Failed to download installer: {e}")
        raise RuntimeError("Failed to download installer") from e


def check_for_client_updates(manual=False, parent=None):
    """
    Check for client updates and prompt the user to update if needed.

    Args:
        manual (bool): Whether this check was triggered manually.
        parent: The parent widget for dialogs.

    Returns:
        bool: True if an update was downloaded and launched, False otherwise.
    """
    try:
        installers = get_client_installers()
        platform_installers = [
            i for i in installers if i["platform"] == settings.platform
        ]

        if not platform_installers:
            if manual:
                QMessageBox.information(
                    parent,
                    "No Updates Found",
                    f"No installers found for platform: {settings.platform}.",
                )
            return False

        latest_installer = max(
            platform_installers, key=lambda i: version.parse(i["version"])
        )

        if is_newer_version(settings.version, latest_installer["version"]):
            reply = QMessageBox.question(
                parent,
                "Client Update Available",
                (
                    f"A new version of the client is available:\n\n"
                    f"Current Version: {settings.version}\n"
                    f"Latest Version: {latest_installer['version']}\n\n"
                    f"Do you want to download and install it now?"
                ),
                QMessageBox.Yes | QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                try:
                    progress_dialog = QProgressDialog(
                        "Downloading update...", "Cancel", 0, 100, parent
                    )
                    progress_dialog.setWindowTitle("Update in Progress")
                    progress_dialog.setWindowModality(Qt.WindowModal)
                    progress_dialog.setMinimumDuration(0)

                    installer_path = download_client_installer(
                        latest_installer, progress_dialog
                    )
                    progress_dialog.close()

                    response = QMessageBox.question(
                        parent,
                        "Update Ready",
                        "The installer is ready to launch. The application will close to proceed. Continue?",
                        QMessageBox.Yes | QMessageBox.No,
                    )
                    if response == QMessageBox.Yes:
                        quit_and_update(installer_path)
                    else:
                        QMessageBox.information(
                            parent,
                            "Update Canceled",
                            "The update process has been canceled.",
                        )
                except Exception as e:
                    QMessageBox.critical(
                        parent,
                        "Update Failed",
                        f"An error occurred while preparing the update:\n{e}",
                    )
        elif manual:
            QMessageBox.information(
                parent, "Client Up To Date", "You are already using the latest version."
            )
        return False
    except Exception as e:
        logger.error(f"Error checking for updates: {e}")
        if manual:
            QMessageBox.critical(
                parent, "Error", f"An error occurred while checking for updates:\n{e}"
            )
        return False


def quit_and_update(installer_path: Path):
    """
    Launch the installer and cleanly quit the client app.

    Args:
        installer_path (Path): Path to the installer.
    """
    try:
        open_file_in_os(installer_path)
        logger.info("Installer launched. Closing the application.")
        QApplication.quit()  # Ensure this is called in the main thread
    except Exception as e:
        logger.error(f"Failed to launch installer: {e}")
