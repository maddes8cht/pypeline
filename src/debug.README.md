# debug.README.md – The Lightweight, Universal Debug/Verbose System

**Current date:** December 2025  
**Location:** `core/debug.py`  
**Used in:** every single script, tool, and notebook in every Python project i work on.

---

### Motivation

Python’s built-in `print()` is pretty handy, but when it comes to debugging or `--verbose`-like flags, you need a minimum of automation to switch output on or off under certain circumstances. The standard `logging` module is too heavy for CLI tools and notebooks, and most custom solutions end up being either too simple (just a global flag) or too complex (full logger hierarchies).

`core/debug.py` solves this once and for all with the **perfect middle ground**:

- **Zero dependencies** – pure Python, < 60 lines  
- **Instantly understandable** – no configuration files, no handlers, no levels  
- **Extremely fast** – only an `if self.enabled` check when disabled  
- **Globally shared** – one `debug` and one `verbose` instance for the entire project  
- **Explicit, safe control** – `.on()` / `.off()` instead of dangerous toggles  
- **Prefix support** – instantly see whether a line is internal debug or user-facing verbose  
- **Fully extensible** – create `warn`, `error`, `success`, etc. in two lines  
- Works equally well in **scripts**, **notebooks**, **REPL sessions**, and **large codebases**

It is deliberately **not** a logging replacement — it is a **printing replacement** for the 99 % of cases where you just want conditional output.

---

### The Two Global Instances

```python
from core.debug import debug, verbose
```

| Instance  | Intended for                  | Prefix (default) | Typical activation |
|-----------|-------------------------------|------------------|---------------------|
| `debug`   | Developer-only diagnostics    | `[DEBUG]   `     | Manually via `debug.on()` (or temporarily in notebooks) |
| `verbose` | User-facing detailed progress | `""` (no prefix) | `--verbose` CLI flag in every tool |

This strict separation is the reason the system never gets confusing.

---

### Basic Usage (in every script)

```python
# At the top of every CLI tool
from core.debug import debug, verbose

parser.add_argument('-v', '--verbose', action='store_true',
                    help='Enable detailed progress output')
args = parser.parse_args()
verbose.enabled = args.verbose   # ← this is the canonical pattern

# Later in the code
verbose.print("Fetching AAPL 1d data...")
debug.print("Cache miss → calling yfinance")
```

### Explicit Control (notebooks / REPL)

```python
from core.debug import debug, verbose

debug.on()          # everything with debug.print() now visible
verbose.off()       # silence user output if desired

# … work …

debug.off()         # turn internal diagnostics off again
```

No hidden toggle magic — you always know exactly what you did.

---

### Creating Additional Named Printers (optional, but very common)

```python
from core.debug import Debug

warn    = Debug(enabled=True,  prefix="[WARNING] ")
error   = Debug(enabled=True,  prefix="[ERROR]   ")
success = Debug(enabled=True,  prefix="[SUCCESS] ")

warn.print("Only 87 rows for TSLA.1d – training will be weak")
error.print("Alpha Vantage API key missing or rate-limited")
success.print("All 312 symbols updated successfully")
```

You can even add colors if your terminal supports it:

```python
critical = Debug(enabled=True, prefix="\033[91m[CRITICAL]\033[0m ")
```

---

### Full Reference – `core/debug.py`

```python
class Debug:
    def __init__(self, enabled: bool = False, prefix: str = ""):
        """
        Args:
            enabled: Start active or inactive (default: False)
            prefix : String printed before every message (e.g. "[DEBUG]   ")
        """
        self.enabled = enabled
        self.prefix = prefix.rstrip() + " " if prefix else ""

    def print(self, *args, **kwargs) -> None:
        """Conditional print with optional prefix."""
        if self.enabled:
            if self.prefix:
                builtins.print(self.prefix, *args, **kwargs)
            else:
                builtins.print(*args, **kwargs)

    def on(self) -> None:
        """Permanently enable this printer."""
        self.enabled = True

    def off(self) -> None:
        """Permanently disable this printer."""
        self.enabled = False


# Global shared instances
debug   = Debug(enabled=False, prefix="[DEBUG]   ")   # developer diagnostics
verbose = Debug(enabled=False, prefix="")             # clean user output
```

---

### Why This Design Was Chosen

| Considered Alternative       | Why it was rejected                                 |
|------------------------------|------------------------------------------------------|
| Full `logging` module        | Too slow, too much boilerplate for CLI tools        |
| Global `DEBUG = False` flag  | No prefixes, no separation of concerns              |
| Toggle method                | Dangerous global state mutation → forgotten toggles |
| Context manager (`with`)     | Hides where output was enabled → hard to audit      |
| Per-module loggers           | Overkill, defeats the purpose of instant simplicity |

The final design is **intentional, explicit, fast, and foolproof**.

---

### Integration Checklist (for every new script)

```python
# 1. Import the instances
from core.debug import debug, verbose

# 2. Add --verbose flag (if it makes sense)
parser.add_argument('-v', '--verbose', action='store_true',
                    help='Show detailed progress')

# 3. Enable verbose for the user
args = parser.parse_args()
verbose.enabled = args.verbose

# 4. Use verbose.print() for anything the user might care about
#    Use debug.print() only for internal diagnostics
```

That’s it. Four lines and you’re fully compliant with the project standard.

---

### Final Words

`debug.py` is deliberately tiny, deliberately global, and deliberately opinionated.  
It is the **one file** that makes every other tool in this repository pleasant to develop and pleasant to use.

Keep it exactly as it is — it has already proven itself across thousands of symbols, dozens of scripts, and countless debugging sessions.

You now have a debug/verbose system that scales from a one-line script to a full-blown trading data platform — without ever getting in your way.

Enjoy the silence when it’s quiet, and the clarity when you need to see what’s really happening.