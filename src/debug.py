import builtins

class Debug:
    """A class to handle conditional debug or verbose printing."""
    
    def __init__(self, enabled: bool = False):
        """Initialize the Debug instance with an enabled flag.
        
        Args:
            enabled (bool): Whether printing is enabled for this instance. Defaults to False.
        """
        self.enabled = enabled

    def print(self, *args, **kwargs) -> None:
        """Prints the provided arguments if the instance is enabled.
        
        Args:
            *args: Variable positional arguments to print.
            **kwargs: Variable keyword arguments to pass to the built-in print function.
        """
        if self.enabled:
            builtins.print(*args, **kwargs)

# Shared instances for debug and verbose output
debug = Debug(enabled=False)  # For debug messages (disabled by default)
verbose = Debug(enabled=False)  # For verbose user information (controlled by --verbose)