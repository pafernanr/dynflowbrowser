"""Loading screen for CSV import with progress bars."""
from textual.app import ComposeResult
from textual.containers import Center
from textual.containers import Middle
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static

from .theme import COLORS, STYLES
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

    def __init__(self, message="Loading Dynflow Data...",
                 show_progress=True, **kwargs):
        """Initialize loading screen.

        Args:
            message: Custom loading message to display
            show_progress: If True, show progress bars; if False, show spinner
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)
        self.message = message
        self.show_progress = show_progress
        self.spinner_index = 0
        self.spinner_timer = None

    def compose(self) -> ComposeResult:
        """Compose the loading screen."""
        with Center():
            with Middle():
                with Vertical():
                    yield LogoBanner()
                    yield Static(
                        self.message,
                        id="loading-label"
                    )
                    with Vertical(id="progress-container"):
                        if self.show_progress:
                            yield Static(
                                "", classes="progress-line", id="progress-tasks"
                            )
                            yield Static(
                                "", classes="progress-line", id="progress-plans"
                            )
                            yield Static(
                                "", classes="progress-line",
                                id="progress-actions"
                            )
                            yield Static(
                                "", classes="progress-line", id="progress-steps"
                            )
                            yield Static(
                                "", classes="progress-line",
                                id="progress-indexes"
                            )
                            yield Static(
                                "", classes="progress-line",
                                id="progress-status"
                            )
                        else:
                            # Show spinner for indeterminate progress
                            yield Static(
                                "", classes="progress-line", id="spinner"
                            )

    def on_mount(self) -> None:
        """Start spinner animation if not showing progress bars."""
        if not self.show_progress:
            self.spinner_timer = self.set_interval(0.1, self._update_spinner)

    def _update_spinner(self) -> None:
        """Update the spinner animation."""
        try:
            spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            widget = self.query_one("#spinner", Static)
            widget.update(
                f"[{COLORS['accent']}]{spinner_chars[self.spinner_index]}[/] "
                "Please wait..."
            )
            self.spinner_index = (self.spinner_index + 1) % len(spinner_chars)
        except Exception:
            pass

    def update_progress(self, dtype, current, total):
        """Update progress for a specific data type.

        Args:
            dtype: Data type (tasks, plans, actions, steps, indexes)
            current: Current progress
            total: Total items
        """
        from rich.text import Text
        try:
            widget = self.query_one(f"#progress-{dtype}", Static)
            if total > 0:
                pct = int(100 * current / total)
                bar_width = 30
                filled = int(bar_width * current / total)
                bar = "█" * filled + "░" * (bar_width - filled)

                text = Text()
                text.append(f"{dtype.capitalize():8s}: ", style=STYLES["key"])
                text.append(f"[{bar}] {pct:3d}%")
                widget.update(text)
            else:
                text = Text()
                text.append(f"{dtype.capitalize():8s}: ", style=STYLES["key"])
                text.append(f"[{'░' * 30}]   0%")
                widget.update(text)
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
