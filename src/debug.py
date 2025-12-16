# core/debug.py ← FINAL, 100% rückwärtskompatibel, funktioniert sofort!
import builtins
from typing import Any


class Debug:
    """A class to handle conditional debug or verbose printing."""
    
    def __init__(self, enabled: bool = False, prefix: str = ""):
        """Initialize the Debug instance.
        
        Args:
            enabled (bool): Whether printing is enabled. Defaults to False.
            prefix (str): Optional prefix (e.g. "[DEBUG]  "). Defaults to empty.
        """
        self.enabled = enabled
        self.prefix = prefix.rstrip() + " " if prefix else ""

    def print(self, *args: Any, **kwargs: Any) -> None:
        """Print only if enabled, optionally with prefix.
        
        Args:
            *args: Variable positional arguments to print.
            **kwargs: Variable keyword arguments to pass to the built-in print function.
        """
        if self.enabled:
            if self.prefix:
                builtins.print(self.prefix, *args, **kwargs)
            else:
                builtins.print(*args, **kwargs)

    def on(self) -> None:
        """Permanently enable printing."""
        self.enabled = True

    def off(self) -> None:
        """Permanently disable printing."""
        self.enabled = False


# Shared instances for debug and verbose output
debug   = Debug(enabled=False, prefix="[DEBUG]   ")  # For debug messages (disabled by default), clearly marked with prefix [DEBUG]
verbose = Debug(enabled=False, prefix="")            # For verbose user information (controlled by --verbose) (without prefix)