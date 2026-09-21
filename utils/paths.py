# =============================================================================
# Utility functions for path manipulation, directory creation, path display,
# and file content type detection (binary vs text).
# =============================================================================

from pathlib import Path  # Object-oriented filesystem paths


# -----------------------------------------------------------------------------
# resolve_path: Standardizes relative/absolute path resolution relative to a working directory
# -----------------------------------------------------------------------------
def resolve_path(base: str | Path, path: str | Path) -> Path:
    """
    Resolves a path to its absolute location on disk.
    If 'path' is already absolute, it returns it directly.
    If 'path' is relative, it resolves it relative to the 'base' directory.
    """
    path = Path(path)

    # If the provided path is already absolute (e.g. "/usr/bin" or "C:\Windows"),
    # normalize symlinks and relative references ('..') and return it.
    if path.is_absolute():
        return path.resolve()

    # Otherwise, resolve the base directory first, then join the relative path using '/'
    return Path(base).resolve() / path


# -----------------------------------------------------------------------------
# display_path_rel_to_cwd: Formats paths nicely for user interface/LLM display
# -----------------------------------------------------------------------------
def display_path_rel_to_cwd(path: str, cwd: Path | None) -> str:
    """
    Attempts to make a path relative to the Current Working Directory (CWD)
    to keep log and UI outputs clean and concise. Fallbacks to original path if impossible.
    """
    try:
        p = Path(path)
    except Exception:
        # If the input path string cannot be parsed into a Path object, return raw string
        return path

    if cwd:
        try:
            # Strip the CWD prefix (e.g., convert '/user/project/src/main.py' to 'src/main.py')
            return str(p.relative_to(cwd))
        except ValueError:
            # Triggers if 'p' is outside 'cwd' or on a different drive letter on Windows
            pass

    # Return normalized path string if relative conversion was not possible
    return str(p)


# -----------------------------------------------------------------------------
# ensure_parent_directory: Safe directory creation helper before writing files
# -----------------------------------------------------------------------------
def ensure_parent_directory(path: str | Path) -> Path:
    """
    Ensures that all parent directories for a given file path exist on disk,
    creating missing nested directories as needed before write operations.
    """
    path = Path(path)

    # path.parent gets the containing folder.
    # parents=True creates intermediate parent folders recursively if missing (like `mkdir -p`).
    # exist_ok=True prevents raising FileExistsError if the directory already exists.
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


# -----------------------------------------------------------------------------
# is_binary_file: Fast heuristic check to prevent attempting to read binary data as text
# -----------------------------------------------------------------------------
def is_binary_file(path: str | Path) -> bool:
    """
    Determines if a file is binary or plain text by reading its initial chunk.
    Returns True if a null byte is found, False if it appears to be text or if unreadable.
    """
    try:
        # Open in binary read mode ('rb') to receive raw bytes instead of decoded strings
        with open(path, "rb") as f:
            # Read an 8 KB sample chunk (8192 bytes = efficient I/O block size)
            chunk = f.read(8192)

            # Text encodings (ASCII, UTF-8) rarely contain null bytes (0x00).
            # If a null byte is present in the chunk, treat it as a binary file.
            return b"\x00" in chunk
    except (OSError, IOError):
        # If file reading fails (e.g., file not found, permission denied), treat as non-binary
        return False
