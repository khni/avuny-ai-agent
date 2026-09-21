# =============================================================================
# This file implements the concrete `ReadFileTool`, which inherits from the base
# `Tool` class. It provides safe, bounded reading of text files on disk,
# formatting output with line numbers, enforcing file size and token limits,
# and preventing attempts to read binary files.
# =============================================================================

from pydantic import BaseModel, Field  # Used for parameter definition and validation

# Import base tool architecture (defined in previous modules)
from tools.base import Tool, ToolInvocation, ToolKind, ToolResult

# Utility functions for filesystem safety and content inspection
from utils.paths import is_binary_file, resolve_path
from utils.text import count_tokens, truncate_text


# -----------------------------------------------------------------------------
# ReadFileParams: Defines and validates input parameters supplied by the LLM
# -----------------------------------------------------------------------------
class ReadFileParams(BaseModel):
    """
    Schema representing all parameters the 'read_file' tool accepts.
    Pydantic automatically validates these fields whenever the tool is invoked.
    """

    path: str = Field(
        ...,  # Ellipsis (...) signifies that this parameter is mandatory/required
        description="Path to the file to read (relative to working directory or absolute)",
    )

    offset: int = Field(
        1,  # Default value is 1 (starts reading from line 1)
        ge=1,  # Constraint: Must be Greater than or Equal to 1 (1-based index)
        description="Line number to start reading from (1-based). Defaults to 1",
    )

    limit: int | None = Field(
        None,  # Optional field; defaults to None (read until end of file)
        ge=1,  # If provided, must be at least 1 line
        description="Maximum number of lines to read. If not specified, reads entire file.",
    )


# -----------------------------------------------------------------------------
# ReadFileTool: Concrete Tool Implementation for File Reading
# -----------------------------------------------------------------------------
class ReadFileTool(Tool):
    # Metadata used by LLMs to select and call this tool
    name = "read_file"
    description = (
        "Read the contents of a text file. Returns the file content with line numbers. "
        "For large files, use offset and limit to read specific portions. "
        "Cannot read binary files (images, executables, etc.)."
    )
    kind = ToolKind.READ  # Categorized as read-only (non-mutating, safe to run)

    # Link the schema class so parent classes know how to validate parameters
    schema = ReadFileParams

    # Safety limits to prevent memory exhaustion or context-window overflow
    MAX_FILE_SIZE = 1024 * 1024 * 10  # Hard stop at 10 MB per file
    MAX_OUTPUT_TOKENS = 25000  # Maximum tokens allowed in LLM context

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """
        Executes the file reading procedure safely with error handling.
        """
        # Step 1: Validate parameters against Pydantic schema and resolve file path
        params = ReadFileParams(**invocation.params)
        path = resolve_path(
            invocation.cwd, params.path
        )  # Prevents directory traversal attacks

        # Step 2: Validate file existence and entry type
        if not path.exists():
            return ToolResult.error_result(f"File not found: {path}")

        if not path.is_file():
            return ToolResult.error_result(f"Path is not a file: {path}")

        # Step 3: Check file size prior to reading into memory
        file_size = path.stat().st_size

        if file_size > self.MAX_FILE_SIZE:
            return ToolResult.error_result(
                f"File too large ({file_size / (1024*1024):.1f}MB). "
                f"Maximum is {self.MAX_FILE_SIZE / (1024*1024):.0f}MB."
            )

        # Step 4: Ensure file is text, not binary (e.g. executable, PNG, ZIP)
        if is_binary_file(path):
            file_size_mb = file_size / (1024 * 1024)
            size_str = (
                f"{file_size_mb:.2f}MB" if file_size_mb >= 1 else f"{file_size} bytes"
            )
            return ToolResult.error_result(
                f"Cannot read binary file: {path.name} ({size_str}) "
                f"This tool only reads text files."
            )

        try:
            # Step 5: Read file text with encoding fallback (UTF-8 first, fallback to Latin-1)
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = path.read_text(encoding="latin-1")

            lines = content.splitlines()
            total_lines = len(lines)

            # Handle empty files gracefully
            if total_lines == 0:
                return ToolResult.success_result(
                    "File is empty.",
                    metadata={
                        "lines": 0,
                    },
                )

            # Step 6: Apply pagination (offset & limit)
            start_idx = max(
                0, params.offset - 1
            )  # Convert 1-based index to 0-based Python slice index

            if params.limit is not None:
                end_idx = min(start_idx + params.limit, total_lines)
            else:
                end_idx = total_lines

            selected_lines = lines[start_idx:end_idx]
            formatted_lines = []

            # Step 7: Format output lines with padded line numbers (e.g. "     1|line content")
            for i, line in enumerate(selected_lines, start=start_idx + 1):
                formatted_lines.append(f"{i:6}|{line}")

            output = "\n".join(formatted_lines)
            token_count = count_tokens(output)

            # Step 8: Truncate output if token limit is exceeded
            truncated = False
            if token_count > self.MAX_OUTPUT_TOKENS:
                output = truncate_text(
                    output,
                    self.MAX_OUTPUT_TOKENS,
                    suffix=f"\n... [truncated {total_lines} total lines]",
                )
                truncated = True

            # Step 9: Add informative header when reading partial file selections
            metadata_lines = []
            if start_idx > 0 or end_idx < total_lines:
                metadata_lines.append(
                    f"Showing lines {start_idx+1}-{end_idx} of {total_lines}"
                )

            if metadata_lines:
                header = " | ".join(metadata_lines) + "\n\n"
                output = header + output

            # Step 10: Return structured result with execution metadata
            return ToolResult.success_result(
                output=output,
                truncated=truncated,
                metadata={
                    "path": str(path),
                    "total_lines": total_lines,
                    "shown_start": start_idx + 1,
                    "shown_end": end_idx,
                },
            )
        except Exception as e:
            # Catch unexpected runtime errors (e.g. permission issues)
            return ToolResult.error_result(f"Failed to read file: {e}")
