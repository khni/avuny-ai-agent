from pathlib import Path
from typing import Any

from platformdirs import user_config_dir, user_data_dir
import tomli

from config.config import Config
from utils.errors import ConfigError
import logging

"""
================================================================================
LOADER FILE
This script hunts down your TOML settings files on your computer, reads them,
merges them together (local settings overwrite global settings), and feeds
them into the Config blueprint we made in the first file.
================================================================================
"""

logger = logging.getLogger(__name__)

# Constants so we don't have to type these filenames repeatedly
CONFIG_FILE_NAME = "config.toml"
AGENT_MD_FILE = "AGENT.MD"


def get_config_dir() -> Path:
    """
    Uses the 'platformdirs' library to find exactly where your specific OS
    (Windows/Mac/Linux) likes to hide global config files, in an 'ai-agent' folder.
    """
    return Path(user_config_dir("ai-agent"))


def get_data_dir() -> Path:
    """Finds the OS-specific folder for background app data."""
    return Path(user_data_dir("ai-agent"))


def get_system_config_path() -> Path:
    """Combines the folder path and the filename to get the exact global config file path."""
    return get_config_dir() / CONFIG_FILE_NAME


def _parse_toml(path: Path):
    """
    Safely opens and reads a .toml file.
    If the file is corrupted, formatted badly, or locked, it catches the crash
    and throws a clean, understandable ConfigError instead.
    """
    try:
        # "rb" means "read binary"
        with open(path, "rb") as f:
            return tomli.load(f)
    except tomli.TOMLDecodeError as e:
        raise ConfigError("Invalid TOML in {path}: {e}", config_file=str(path)) from e
    except (OSError, IOError) as e:
        raise ConfigError(
            "Failed to read config file {path}: {e}", config_file=str(path)
        ) from e


def _get_project_config(cwd: Path) -> Path | None:
    """
    Looks in your current working directory (cwd) for a hidden folder named '.ai-agent'.
    If it finds a 'config.toml' inside there, it returns the path. If not, it returns None.
    """
    current = cwd.resolve()
    agent_dir = current / ".ai-agent"

    if agent_dir.is_dir():
        config_file = agent_dir / CONFIG_FILE_NAME
        if config_file.is_file():
            return config_file

    return None


def _get_agent_md_files(cwd: Path) -> Path | None:
    """
    Looks in your current working directory for a file named 'AGENT.MD'.
    If found, it reads all the text inside and returns it.
    """
    current = cwd.resolve()

    if current.is_dir():
        agent_md_file = current / AGENT_MD_FILE
        if agent_md_file.is_file():
            content = agent_md_file.read_text(encoding="utf-8")
            return content

    return None


def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """
    The "Tie-Breaker" function.
    It takes two dictionaries (the global config and the local project config).
    If a setting exists in both, the 'override' (local) value overwrites the 'base' value.
    This allows local projects to have custom settings without deleting global ones.
    """
    result = base.copy()
    for key, value in override.items():
        # If the value is a dictionary itself (like mcp_servers), we have to merge it recursively
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_dicts(result[key], value)
        else:
            # Otherwise, just overwrite the value directly
            result[key] = value

    return result


def load_config(cwd: Path | None) -> Config:
    """
    THE MAIN EVENT. This is the orchestrator that actually runs everything.
    It returns a fully validated 'Config' object (from our first file).
    """
    # 1. Figure out where we are currently working
    cwd = cwd or Path.cwd()
    system_path = get_system_config_path()
    config_dict: dict[str, Any] = {}

    # 2. Try to read the Global/System config file
    if system_path.is_file():
        try:
            config_dict = _parse_toml(system_path)
        except ConfigError:
            # If it's invalid, just warn the user and keep going
            logger.warning(f"Skipping invalid system config: {system_path}")

    # 3. Try to read the Local/Project config file
    project_path = _get_project_config(cwd)
    if project_path:
        try:
            project_config_dict = _parse_toml(project_path)
            # 4. Merge the two files together (Local overrides Global)
            config_dict = _merge_dicts(config_dict, project_config_dict)
        except ConfigError:
            # NOTE: There's a small bug here in original code - it says `system_path` in the
            # warning instead of `project_path`
            logger.warning(f"Skipping invalid system config: {system_path}")

    # 5. Inject the current working directory into the dictionary if it isn't there
    if "cwd" not in config_dict:
        config_dict["cwd"] = cwd

    # 6. Look for AGENT.MD instructions. If found, add them to developer_instructions.
    if "developer_instructions" not in config_dict:
        agent_md_content = _get_agent_md_files(cwd)
        if agent_md_content:
            config_dict["developer_instructions"] = agent_md_content

    # 7. The Grand Finale: Take this giant dictionary of settings and feed it
    # into the strict Pydantic `Config` blueprint we created in `config.py`.
    # Pydantic will do all the type-checking, validation, and defaulting right here.
    try:
        config = Config(**config_dict)
    except Exception as e:
        # If Pydantic finds a problem (like a timeout is a string instead of a float), it fails here.
        raise ConfigError(f"Invalid configuration: {e}") from e

    return config
