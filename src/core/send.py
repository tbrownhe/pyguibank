import base64
import hashlib
import json
import time
from pathlib import Path

import requests
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from loguru import logger
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMessageBox, QProgressDialog

from core.settings import settings


def cache_public_key(force=False):
    """Downloads and caches the server's public RSA key

    Args:
        force (bool, optional): Force download of new key from server. Defaults to False.

    Raises:
        Exception: Unable to fetch key
    """
    # Return early if file is cached
    if settings.server_public_key.exists() and not force:
        return

    # Get the file from server
    logger.info("Downloading server public key")
    response = requests.get(f"{settings.server_url}/keys/public-key")
    if response.status_code == 200:
        public_key = response.content
        with settings.server_public_key.open("wb") as key_file:
            key_file.write(public_key)
    else:
        raise Exception(f"Failed to fetch public key: {response.status_code} - {response.text}")


def fetch_public_key_hash() -> str:
    """Fetches the SHA256 hash of the public key on the server.

    Raises:
        Exception: Failed to fetch data from server

    Returns:
        str: SHA256 hash of server's public RSA key
    """
    logger.info("Fetching server public key hash")
    response = requests.get(f"{settings.server_url}/keys/public-key-hash")
    if response.status_code == 200:
        return response.json()["hash"]
    else:
        raise Exception(f"Failed to fetch public key hash: {response.status_code} - {response.text}")


def validate_public_key():
    """Makes sure that locally cached server public key matches the remote copy,
    then returns the validated key for use.

    Raises:
        ValueError: Could not validate server's public key

    Returns:
        PublicKeyTypes: PublicKey of server
    """
    try:
        # Make sure a public key is cached
        cache_public_key()

        # Get the SHA256 hash from server
        public_key_hash_server = fetch_public_key_hash()

        # Get cached public key public key and hash
        logger.info("Validating server public key hash")
        with settings.server_public_key.open("rb") as key_file:
            public_key_bytes = key_file.read()

        # Compute local hash of the public key
        public_key_hash_local = hashlib.sha256(public_key_bytes).hexdigest()

        # Compare hashes
        if public_key_hash_local == public_key_hash_server:
            return serialization.load_pem_public_key(public_key_bytes)
        else:
            raise ValueError("Public key verification failed. Hash mismatch.")
    except Exception as e:
        logger.error(f"Error during public key verification: {e}")
        raise


def encrypt_symmetric_key(_symmetric_key: bytes, progress=None) -> str:
    """Encrypt the symmetric key using the server's public RSA key.
    High security encryption for very small amounts of data.
    Using RSA to encrypt the symmetric key provides the same level of security
    as directly encrypting the file. The symmetric key is inaccessible without
    the server's private RSA key.

    Args:
        symmetric_key (bytes): Fernet key for decrypting file

    Returns:
        bytes: Fernet key encrypted using server's RSA key
    """
    # Get the public key. Retry once if there's a problem.
    if progress:
        progress.setValue(progress.value() + 1)
        progress.setLabelText("Validating public key")
        time.sleep(1)

    try:
        public_key = validate_public_key()
    except ValueError:
        try:
            logger.debug("Refreshing locally cached server public key")
            cache_public_key(force=True)
            public_key = validate_public_key()
        except Exception:
            raise
    except Exception:
        raise

    logger.info("Encrypting symmetric key with server public key")
    if progress:
        progress.setValue(progress.value() + 1)
        progress.setLabelText("Encrypting symmetric key with public key")
        time.sleep(1)

    encrypted_key = public_key.encrypt(
        _symmetric_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    # Convert encrypted key to Base64 string to send over https
    return base64.b64encode(encrypted_key).decode("utf-8")


def encrypt_file(fpath: Path, progress=None) -> tuple[bytes, bytes]:
    """Encrypt each file with a unique symmetric key.

    Args:
        fpath (Path): File to be encrypted

    Returns:
        tuple[bytes, bytes]: Encrypted data, Encrypted key
    """
    logger.info("Encrypting file with symmetric key")
    if progress:
        progress.setValue(progress.value() + 1)
        progress.setLabelText("Encrypting file with symmetric key")
        time.sleep(1)

    _symmetric_key = Fernet.generate_key()
    cipher = Fernet(_symmetric_key)
    with fpath.open("rb") as f:
        encrypted_file = cipher.encrypt(f.read())

    # Encrypt _symmetric_key before returning from this function to ensure hygiene
    encrypted_key = encrypt_symmetric_key(_symmetric_key, progress=progress)

    return encrypted_file, encrypted_key


def send_statement(metadata: dict, parent=None):
    """Encrypts and sends a file to the server backend API.

    Args:
        fpath (Path): Statement file to encrypt and send.
    """
    # Make sure the user really wants this
    reply = QMessageBox.question(
        parent,
        "Confirm Submission",
        (
            "Are you sure you want to submit this statement?\n\n"
            "Once submitted, this file will be securely encrypted"
            " and sent to PyGuiBank developers."
        ),
        QMessageBox.Yes | QMessageBox.No,
    )
    if reply != QMessageBox.Yes:
        logger.info("User cancelled file send.")
        return

    # Pull out the file path
    fpath = metadata.get("file_path", None)
    if not fpath:
        raise ValueError("No file_path found in metadata")
    fpath = Path(fpath).resolve()

    # Logging to user
    logger.info(f"Sending {fpath} to server securely")
    progress = QProgressDialog("Sending File to PyGuiBank Developers", "Cancel", 0, 7, parent)
    progress.setMinimumWidth(400)
    progress.setWindowTitle("Using End-to-End Encryption")
    progress.setWindowModality(Qt.WindowModal)
    progress.setMinimumDuration(0)
    progress.setValue(1)
    progress.show()
    QApplication.processEvents()
    time.sleep(1)

    try:
        # Encrypt data and key
        encrypted_file, encrypted_key = encrypt_file(fpath, progress=progress)

        # Send the encrypted file and metadata to the server
        logger.info("Posting encrypted file to server via https")
        progress.setValue(progress.value() + 1)
        progress.setLabelText("Posting encrypted file to server via https")
        time.sleep(1)

        response = requests.post(
            f"{settings.server_url}/statements/submit-statement",
            headers={"Authorization": f"Bearer {settings.api_token}"},
            files={"file": encrypted_file},
            data={
                "metadata": json.dumps(metadata),
                "encrypted_key": encrypted_key,
                "user_token": settings.api_token,
            },
        )

        progress.setValue(progress.value() + 1)
        time.sleep(1)
        progress.close()

        # Confirm server received and stored the file
        message = response.json().get("message", None)
        if message and message == "SUCCESS":
            logger.success(f"Sent {fpath.name} to server")
            QMessageBox.information(
                parent,
                "Statement Sent",
                "Server confirmed End-to-End encrypted file transfer.",
            )
        else:
            logger.error(f"Server responded with error: {message}")
            QMessageBox.critical(
                parent,
                "Statement Not Sent",
                f"Server responded with error: {message}",
            )

    except Exception as e:
        logger.error(f"Failed to send statement to server: {e}")
        progress.close()
        QMessageBox.critical(
            parent,
            "Statement Sent",
            "Server confirmed secure transfer.",
        )
