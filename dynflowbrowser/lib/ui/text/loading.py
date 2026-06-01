"""Loading screen for CSV import with progress bars."""
from textual.app import ComposeResult
from textual.containers import Center
from textual.containers import Middle
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static

from .widgets import LogoBanner


class LoadingScreen(Screen):
    """Loading screen with ASCII art and progress information."""

    CSS = """
    LoadingScreen {
        align: center middle;
        background: $surface;
    }

    LogoBanner {
        margin: 0 0 1 0;
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

    def compose(self) -> ComposeResult:
        """Compose the loading screen."""
        with Center():
            with Middle():
                with Vertical():
                    yield LogoBanner()
                    yield Static(
                        "Loading Dynflow Data...",
                        id="loading-label"
                    )
                    with Vertical(id="progress-container"):
                        yield Static(
                            "", classes="progress-line", id="progress-tasks"
                        )
                        yield Static(
                            "", classes="progress-line", id="progress-plans"
                        )
                        yield Static(
                            "", classes="progress-line", id="progress-actions"
                        )
                        yield Static(
                            "", classes="progress-line", id="progress-steps"
                        )
                        yield Static(
                            "", classes="progress-line", id="progress-indexes"
                        )
                        yield Static(
                            "", classes="progress-line", id="progress-status"
                        )

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
