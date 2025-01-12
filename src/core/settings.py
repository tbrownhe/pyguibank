import platform
from pathlib import Path
from platform import system

from loguru import logger
from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from version import __version__

# Platform dependence
APPDATA_DIR = (
    Path.home() / "AppData/Roaming/PyGuiBank"
    if system() == "Windows"
    else (
        Path.home() / "Library/Application Support/PyGuiBank"
        if system() == "Darwin"
        else Path.home() / ".config/PyGuiBank"
    )
)


def get_platform():
    """
    Detect the current platform for the client.

    Returns:
        str: Platform identifier (e.g., 'win64', 'macos', 'linux').
    """
    system = platform.system().lower()
    arch = platform.architecture()[0]

    if system == "windows":
        return "win64" if "64" in arch else "win32"
    elif system == "darwin":
        return "macos"
    elif system == "linux":
        return "linux"
    else:
        return "unknown"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
    )

    # Current platform and client version
    platform: str = get_platform()
    version: str = __version__

    # Load from .env or fallback to defaults
    server_url: AnyHttpUrl = Field(
        "http://pyguibank.com:8000/api/v1", validation_alias="PYGUIBANK_SERVER_URL"
    )
    config_path: Path = Field(
        APPDATA_DIR / "config.ini",
        validation_alias="PYGUIBANK_CONFIG_PATH",
    )
    plugin_dir: Path = Field(
        APPDATA_DIR / "plugins",
        validation_alias="PYGUIBANK_PLUGIN_DIR",
    )
    log_dir: Path = Field(
        APPDATA_DIR / "logs",
        validation_alias="PYGUIBANK_LOG_DIR",
    )
    statement_types_json: Path = Field(APPDATA_DIR / "init_statement_types.json")
    accounts_json: Path = Field(APPDATA_DIR / "init_accounts.json")


settings = AppSettings()

logger.info(f"server_url: {settings.server_url}")
logger.info(f"config_path: {settings.config_path}")
logger.info(f"plugin_dir: {settings.plugin_dir}")
logger.info(f"log_dir: {settings.log_dir}")
