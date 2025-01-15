import shutil
import sys
from pathlib import Path
from loguru import logger
from core.settings import settings
from core.utils import create_directory


def initialize_plugins():
    """
    Copies bundled plugins to the user plugin directory if they don't exist.
    """
    plugin_bundled_dir = (
        Path("plugins") if hasattr(sys, "_MEIPASS") else Path("dist/plugins")
    ).resolve()

    try:
        if not settings.plugin_dir.exists():
            if not plugin_bundled_dir.exists():
                create_directory(settings.plugin_dir)
                logger.debug(
                    f"Bundled plugins not found in {plugin_bundled_dir}, skipping"
                )
            else:
                shutil.copytree(plugin_bundled_dir, settings.plugin_dir)
                logger.debug(
                    f"Copied bundled plugins from {plugin_bundled_dir} to {settings.plugin_dir}"
                )
    except Exception as e:
        logger.error(f"Failed to initialize plugins: {e}")


def seed_account_types():
    account_types = [
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
    return account_types
