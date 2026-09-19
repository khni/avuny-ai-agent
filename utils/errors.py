from typing import Any

"""
================================================================================
ERRORS FILE
Think of this file as the "Alarm System" for your application. 
It defines custom error types. This way, when the program crashes, it doesn't 
just show a confusing wall of red text. It gives you a neat, organized report 
of exactly what went wrong.
================================================================================
"""


# 'Exception' is Python's built-in, default alarm bell.
# By putting (Exception) here, we are saying: "Make AgentError act exactly like a
# normal Python error, but with our own custom upgrades."
class AgentError(Exception):
    """
    The Master Alarm Bell for the AI Agent.
    Every single error that happens in this app will be a type of AgentError.
    """

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        The setup process when the alarm is triggered.
        - message: A human-readable sentence about what broke.
        - details: A dictionary of clues (like exactly what data caused the crash).
        - cause: Sometimes an error is triggered by a *different* error hidden underneath.
                 This lets us attach the original "root cause" error.
        """
        # super().__init__(message) means: "Hey Parent (the built-in Python Exception),
        # do your normal setup process with this message first!"
        super().__init__(message)

        # Then, we save our custom extra clues to this specific alarm bell.
        self.message = message
        # If they didn't provide details, default to an empty dictionary {}
        self.details = details or {}
        self.cause = cause

    def __str__(self) -> str:
        """
        The "Print" Translator.
        If a programmer types `print(error)`, Python looks for this exact function
        to know how to turn the error into a readable sentence on the screen.
        """
        # Start with the basic error message (e.g., "Failed to connect")
        base = self.message

        # If we have extra clues, stitch them together and add them to the message.
        if self.details:
            # This creates a string like: "port=8080, user=admin"
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            # Now the message looks like: "Failed to connect (port=8080, user=admin)"
            base = f"{base} ({detail_str})"

        # If this error was caused by a deeper underlying error, attach that too!
        if self.cause:
            base = f"{base} [caused by: {self.cause}]"

        # Hand the perfectly formatted sentence back to the screen.
        return base

    def to_dict(self) -> dict[str, Any]:
        """
        The "Logbook" Translator.
        While `__str__` is for human eyes, `to_dict` turns the error into a neat
        data dictionary. This is super useful if you want to save your errors
        to a database or a JSON log file to analyze later.
        """
        return {
            # self.__class__.__name__ gets the exact name of the error (e.g., "AgentError")
            "type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            # If there's a root cause, turn it into text. Otherwise, put None.
            "cause": str(self.cause) if self.cause else None,
        }


# By putting (AgentError) here, we are saying: "ConfigError inherits EVERYTHING
# from AgentError (the setup, the print translator, the dict translator), but
# we are going to tweak it slightly for configuration problems."
class ConfigError(AgentError):
    """
    A Specific Alarm Bell just for Settings/Configuration issues.
    (Like a fire alarm vs. a burglar alarm).
    """

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        config_file: str | None = None,
        # **kwargs means "accept any extra miscellaneous arguments they throw at us"
        **kwargs: Any,
    ) -> None:
        """
        Setup process specifically for broken settings.
        Instead of just asking for general 'details', it explicitly asks:
        "Which setting name broke?" (config_key) and "Which file was it in?" (config_file).
        """
        # Grab any extra details passed in, or make an empty dictionary.
        details = kwargs.pop("details", {}) or {}

        # If they told us which setting broke, add it to our clues dictionary.
        if config_key:
            details["config_key"] = config_key

        # If they told us which file it was in, add that to our clues too.
        if config_file:
            details["config_file"] = config_file

        # Now, pass the baton UP to the parent class (AgentError).
        # We hand it our message and our fully packed 'details' bag so it can do the rest.
        super().__init__(message, details=details, **kwargs)

        # Finally, save these specific variables to this object just in case we
        # need to look at them directly later.
        self.config_key = config_key
        self.config_file = config_file
