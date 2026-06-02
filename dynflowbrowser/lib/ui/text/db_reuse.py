"""Database reuse confirmation screen for TUI."""
import os

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center
from textual.containers import Horizontal
from textual.containers import Middle
from textual.containers import Vertical
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Button
from textual.widgets import Footer
from textual.widgets import Static

from .theme import STYLES
from .widgets import LogoBanner


class DatabaseReuseScreen(Screen):
    """Screen to confirm database reuse or overwrite."""

    BINDINGS = [
        Binding("q", "request_quit", "Quit", priority=True),
        Binding("escape", "request_quit", "Quit", show=True),
        Binding("left", "previous_button", "", show=False),
        Binding("right", "next_button", "", show=False),
    ]

    CSS = """
    DatabaseReuseScreen {
        background: $surface;
    }

    #main-content {
        align: center middle;
        height: 1fr;
    }

    LogoBanner {
        width: 100%;
        margin: 0;
    }

    #title {
        width: 100%;
        text-align: center;
        text-style: bold;
        color: $warning;
        margin: 1 0;
        padding: 0 2;
    }

    #db-path {
        width: 100%;
        text-align: center;
        margin: 0 0 1 0;
        padding: 0 2;
        color: $text-muted;
    }

    #filters-section {
        width: 100%;
        height: auto;
        max-height: 15;
        margin: 1 2;
        background: $panel;
        border: solid $primary;
    }

    #filters-content {
        width: 100%;
        color: $text;
    }

    #message {
        width: 100%;
        text-align: center;
        margin: 1 2;
        padding: 0 2;
    }

    #button-container {
        width: 100%;
        height: auto;
        align: center middle;
        margin: 1 0;
        padding: 0 0 1 0;
    }

    Button {
        width: 20;
        height: 3;
        margin: 0 1;
    }

    Button:focus {
        text-style: bold reverse;
    }
    """

    def __init__(self, conf):
        """Initialize database reuse modal.

        Args:
            conf: Configuration object with database and args info
        """
        super().__init__()
        self.conf = conf

    def compose(self) -> ComposeResult:
        """Compose the database reuse screen."""
        with Center(id="main-content"):
            with Middle():
                with Vertical():
                    # ASCII art logo at top
                    yield LogoBanner()

                    yield Static(
                        "Database Already Exists",
                        id="title"
                    )

                    # Show database path
                    rel_path = os.path.relpath(self.conf.dbfile, self.conf.cwd)
                    yield Static(
                        f"File: {rel_path}",
                        id="db-path"
                    )

                    # Show filters (previous and current)
                    with VerticalScroll(id="filters-section"):
                        yield Static("", id="filters-content")

                    # Explanation message
                    yield Static(
                        "[#3f9c35]Reuse[/#3f9c35]: Keep existing data and filters\n"
                        "[#c9190b]Overwrite[/#c9190b]: Delete and rebuild "
                        "with current filters",
                        id="message"
                    )

                    # Buttons
                    with Center():
                        with Horizontal(id="button-container"):
                            yield Button(
                                "Reuse",
                                variant="success",
                                id="reuse-btn"
                            )
                            yield Button(
                                "Overwrite",
                                variant="error",
                                id="overwrite-btn"
                            )

        yield Footer()

    def on_mount(self) -> None:
        """Load and display previous and current filters when mounted."""
        self._load_filters()
        # Focus on Reuse button by default
        self.query_one("#reuse-btn", Button).focus()

    def _load_filters(self) -> None:
        """Load and display previous and current filters."""
        from rich.text import Text

        filters_widget = self.query_one("#filters-content", Static)
        text = Text()

        # Load previous filters from file
        previous_filters = []
        if os.path.exists(self.conf.argsfile):
            try:
                with open(self.conf.argsfile, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                in_filters = False
                for line in lines:
                    line = line.strip()
                    if line.startswith("Filters:"):
                        in_filters = True
                        if "None" in line:
                            previous_filters.append(
                                "No filters (showing all tasks)"
                            )
                            break
                    elif in_filters and line.startswith("-"):
                        previous_filters.append(line[2:].strip())
                    elif in_filters and line and not line.startswith("-"):
                        break
            except Exception:
                pass

        # Build current filter list
        current_filters = []
        if self.conf.args.search:
            current_filters.append(f"Search: {self.conf.args.search}")
        if self.conf.args.state:
            current_filters.append(f"State: {self.conf.args.state}")
        if self.conf.args.result:
            current_filters.append(f"Result: {self.conf.args.result}")
        if self.conf.args.task_days:
            current_filters.append(f"Task Days: {self.conf.args.task_days}")

        # Display previous filters
        text.append("Previous Filters:\n", style=STYLES["success_text"])
        if previous_filters:
            for f in previous_filters:
                text.append(f"  • {f}\n")
        else:
            text.append("  No filter information available\n", style=STYLES["dim"])

        # Display current filters
        text.append("Current Filters:\n", style=STYLES["warning_text"])
        if current_filters:
            for i, f in enumerate(current_filters):
                if i < len(current_filters) - 1:
                    text.append(f"  • {f}\n")
                else:
                    text.append(f"  • {f}")
        else:
            text.append("  No filters (showing all tasks)", style=STYLES["dim"])

        filters_widget.update(text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press and proceed with the decision."""
        reuse = None
        if event.button.id == "reuse-btn":
            reuse = True
        elif event.button.id == "overwrite-btn":
            reuse = False

        if reuse is not None:
            # Call the handler on the app
            self.app._handle_db_reuse_decision(reuse)

    def action_previous_button(self) -> None:
        """Focus previous button."""
        self.screen.focus_previous()

    def action_next_button(self) -> None:
        """Focus next button."""
        self.screen.focus_next()

    def action_request_quit(self) -> None:
        """Request quit confirmation."""
        self.app.action_request_quit()
