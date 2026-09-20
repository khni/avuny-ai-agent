from __future__ import annotations
from enum import Enum
import os
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field, model_validator
from dotenv import load_dotenv

load_dotenv()

"""
================================================================================
CONFIG FILE
This file uses a library called 'pydantic'. Pydantic lets us create strict
"blueprints" (called BaseModels). Whenever we create a setting, pydantic
automatically checks if it's the right data type (like making sure a number
is actually a number and not a word).
================================================================================
"""


class ModelConfig(BaseModel):
    """
    Blueprint for the AI Model's brain settings.
    """

    # The default AI model we want to use if the user doesn't pick one.
    name: str = "deepseek/deepseek-v4.1-flash"

    # Temperature controls creativity. ge=0.0 means "Greater than or Equal to 0",
    # le=2.0 means "Less than or Equal to 2". Pydantic enforces this rule!
    temperature: float = Field(default=1, ge=0.0, le=2.0)

    # How many "tokens" (words/pieces of text) the AI can remember at once.
    context_window: int = 256_000
    
    # How many tokens the AI can generate in a single response. This is a safety limit.
    max_tokens: int = 4096


class ShellEnvironmentPolicy(BaseModel):
    """
    Blueprint for how the AI interacts with your computer's terminal.
    """

    ignore_default_excludes: bool = False

    # Security feature: A list of patterns to hide from the AI so it doesn't
    # accidentally read or leak your secret passwords/keys.
    exclude_patterns: list[str] = Field(
        default_factory=lambda: ["*KEY*", "*TOKEN*", "*SECRET*"]
    )

    # Allows setting custom environment variables for the AI to use.
    set_vars: dict[str, str] = Field(default_factory=dict)


class MCPServerConfig(BaseModel):
    """
    Blueprint for connecting the AI to external tools or servers (MCP).
    """

    enabled: bool = True
    startup_timeout_sec: float = 10

    # Option 1: stdio transport (running a local command on your computer)
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    cwd: Path | None = None

    # Option 2: http/sse transport (connecting via a URL over the internet)
    url: str | None = None

    @model_validator(mode="after")
    def validate_transport(self) -> MCPServerConfig:
        """
        This is an automatic safety check that runs after the blueprint is filled out.
        It ensures you only provide ONE connection method: command OR url.
        """
        has_command = self.command is not None
        has_url = self.url is not None

        # If they didn't provide either one, crash and complain.
        if not has_command and not has_url:
            raise ValueError(
                "MCP Server must have either 'command' (stdio) or 'url' (http/sse)"
            )

        # If they provided BOTH, crash and complain.
        if has_command and has_url:
            raise ValueError(
                "MCP Server cannot have both 'command' (stdio) and 'url' (http/sse)"
            )

        # If everything is fine, return the validated settings.
        return self


class ApprovalPolicy(str, Enum):
    """
    A simple list of fixed choices for when the AI needs human permission to act.
    Using an Enum prevents someone from typing a typo like "awn-request".
    """

    ON_REQUEST = "on-request"
    ON_FAILURE = "on-failure"
    AUTO = "auto"
    AUTO_EDIT = (
        "auto-edut"  # Note: there appears to be a typo here in the original code!
    )
    NEVER = "never"
    YOLO = "yolo"


class HookTrigger(str, Enum):
    """
    A list of fixed choices defining exactly WHEN a custom script (hook) should run.
    """

    BEFORE_AGENT = "before_agent"
    AFTER_AGENT = "after_agent"
    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"
    ON_ERROR = "on_error"


class HookConfig(BaseModel):
    """
    Blueprint for creating a single "Hook" (a custom script that runs automatically).
    """

    name: str
    trigger: HookTrigger
    command: str | None = None  # e.g., "python3 tests.py"
    script: str | None = None  # e.g., "*.sh"
    timeout_sec: float = 30
    enabled: bool = True

    @model_validator(mode="after")
    def validate_hook(self) -> HookConfig:
        """
        Automatic safety check: ensure the user actually provided a command or script to run.
        """
        if not self.command and not self.script:
            raise ValueError("Hook must either have 'command' or 'script'")
        return self


class Config(BaseModel):
    """
    THE MASTER BLUEPRINT.
    This groups all the smaller blueprints above into one massive master settings object.
    """

    # Bring in the ModelConfig from above
    model: ModelConfig = Field(default_factory=ModelConfig)

    # Where on the computer the AI is currently working
    cwd: Path = Field(default_factory=Path.cwd)

    # Bring in the shell security policy from above
    shell_environment: ShellEnvironmentPolicy = Field(
        default_factory=ShellEnvironmentPolicy
    )

    hooks_enabled: bool = False
    hooks: list[HookConfig] = Field(default_factory=list)
    approval: ApprovalPolicy = ApprovalPolicy.ON_REQUEST
    max_turns: int = 100
    mcp_servers: dict[str, MCPServerConfig] = Field(default_factory=dict)

    allowed_tools: list[str] | None = Field(
        None,
        description="If set, only these tools will be available to the agent",
    )

    developer_instructions: str | None = None
    user_instructions: str | None = None
    debug: bool = False

    # The @property decorator makes a function act like a regular variable.
    # So you can just ask for `config.api_key` instead of `config.api_key()`.
    @property
    def api_key(self) -> str | None:
        # Sneaks a peek into the computer's environment variables to find the API key
        return os.environ.get("API_KEY")

    @property
    def base_url(self) -> str | None:
        return os.environ.get("BASE_URL")

    # These getters/setters are shortcuts so you don't have to type `config.model.name`
    @property
    def model_name(self) -> str:
        return self.model.name

    @model_name.setter
    def model_name(self, value: str) -> None:
        self.model.name = value

    @property
    def temperature(self) -> float:
        return self.model.temperature

    @temperature.setter
    def temperature(self, value: str) -> None:
        self.model.temperature = value

    @property
    def max_tokens(self) -> int:
        return self.model.max_tokens

    @max_tokens.setter
    def max_tokens(self, value: int) -> None:
        self.model.max_tokens = value

    def validate(self) -> list[str]:
        """
        A final sanity check to make sure the AI has everything it needs to start.
        Returns a list of errors if anything is missing.
        """
        errors: list[str] = []

        if not self.api_key:
            errors.append("No API key found. Set API_KEY environment variable")

        if not self.cwd.exists():
            errors.append(f"Working directory does not exist: {self.cwd}")

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Converts this complex object back into a standard Python dictionary."""
        return self.model_dump(mode="json")
