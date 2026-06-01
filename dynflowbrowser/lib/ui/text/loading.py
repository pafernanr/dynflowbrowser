"""Loading screen for CSV import with progress bars."""
import os

from textual.app import ComposeResult
from textual.containers import Center
from textual.containers import Middle
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static


class LoadingScreen(Screen):
    """Loading screen with ASCII art and progress information."""

    CSS = """
    LoadingScreen {
        align: center middle;
        background: $surface;
    }

    #ascii-art {
        width: auto;
        height: auto;
        text-style: bold;
        color: $accent;
        margin: 0 0 1 0;
    }

    #version-label {
        width: 100%;
        text-align: left;
        color: $text-muted;
        margin: 0 0 1 2;
    }

    #loading-label {
        width: 100%;
        text-align: center;
        margin: 1 0;
        text-style: bold;
        color: $warning;
    }

    #progress-container {
        width: 100%;
        height: auto;
        min-height: 6;
        margin: 2 0 0 0;
    }

    .progress-line {
        width: 100%;
        text-align: center;
        margin: 0 0;
    }
    """

    def __init__(self):
        """Initialize loading screen."""
        super().__init__()
        # Get version from config
        fname = os.path.join(
            os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.dirname(__file__))
            )),
            '__VERSION__'
        )
        with open(fname, encoding="utf-8") as f:
            self.version = f.read().strip()

    def compose(self) -> ComposeResult:
        """Compose the loading screen."""
        # Same ASCII art as welcome screen
        ascii_art = """


  _____              ______ _               ____
 |  __ \\            |  ____| |             |  _ \\
 | |  | |_   _ _ __ | |__  | | _____      _| |_) |_ __ _____      _____  ___ _ __
 | |  | | | | | '_ \\|  __| | |/ _ \\ \\ /\\ / /  _ <| '__/ _ \\ \\ /\\ / / __|/ _ \\ '__|
 | |__| | |_| | | | | |    | | (_) \\ V  V /| |_) | | | (_) \\ V  V /\\__ \\  __/ |
 |_____/ \\__, |_| |_|_|    |_|\\___/ \\_/\\_/ |____/|_|  \\___/ \\_/\\_/ |___/\\___|_|
          __/ |
         |___/"""  # noqa: E501

        with Center():
            with Middle():
                with Vertical():
                    yield Static(ascii_art, id="ascii-art")
                    yield Static(self.version, id="version-label")
                    yield Static(
                        "Loading Dynflow Data...",
                        id="loading-label"
                    )
                    with Vertical(id="progress-container"):
                        yield Static("", classes="progress-line", id="progress-tasks")
                        yield Static("", classes="progress-line", id="progress-plans")
                        yield Static("", classes="progress-line", id="progress-actions")
                        yield Static("", classes="progress-line", id="progress-steps")
                        yield Static("", classes="progress-line", id="progress-indexes")
                        yield Static("", classes="progress-line", id="progress-status")

    def update_progress(self, dtype, current, total):
        """Update progress for a specific data type.

        Args:
            dtype: Data type (tasks, plans, actions, steps, indexes)
            current: Current progress
            total: Total items
        """
        try:
            widget = self.query_one(f"#progress-{dtype}", Static)
            if total > 0:
                pct = int(100 * current / total)
                bar_width = 30
                filled = int(bar_width * current / total)
                bar = "█" * filled + "░" * (bar_width - filled)
                widget.update(f"{dtype.capitalize():8s}: [{bar}] {pct:3d}%")
            else:
                widget.update(f"{dtype.capitalize():8s}: [{'░' * 30}]   0%")
        except Exception:
            pass

    def update_status(self, message):
        """Update status message.

        Args:
            message: Status message to display
        """
        try:
            widget = self.query_one("#progress-status", Static)
            widget.update(message)
        except Exception:
            pass
