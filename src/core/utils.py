# -*- coding: utf-8 -*-
from pathlib import Path
import configparser


def p(val):
    """
    Print out the contents of val and stop the script.
    """
    if isinstance(val, list):
        for item in val:
            print(item)
    else:
        print(val)
    exit()


def read_config(config_path: Path):
    """
    Uses ConfigParser to get the contents of the config.ini file.
    """
    # Check to see if the config file exists
    if not config_path.exists:
        raise ValueError(
            "Please create and populate a config.txt file in the root directory."
        )

    # Open the config file
    config = configparser.ConfigParser()
    config.read(config_path)

    return config
