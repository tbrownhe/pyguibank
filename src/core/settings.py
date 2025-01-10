from pathlib import Path
from platform import system

from loguru import logger
from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
    )

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
