"""Database reuse confirmation screen for TUI."""
import os

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center
from textual.containers import Horizontal
from textual.containers import Middle
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button
from textual.widgets import Footer
from textual.widgets import Static

from .theme import COLORS, STYLES
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

    #db-info {
        width: 100%;
        text-align: center;
        margin: 1 0;
        padding: 0 2;
    }

    #filters-container {
        width: 100%;
        height: auto;
        margin: 1 2;
    }

    #filters-box {
        width: 100%;
        height: auto;
        border: solid $primary;
        padding: 1;
    }

    #filters-columns {
        width: 100%;
        height: auto;
    }

    #previous-filters, #current-filters {
        width: 1fr;
        height: auto;
        padding: 0 1;
        align: center top;
    }

    .filter-content {
        width: auto;
        height: auto;
        text-align: left;
    }

    #message {
        width: 100%;
        height: auto;
        margin: 1 0;
        padding: 0;
    }

    #spacer {
        height: 2;
    }

    #message-columns {
        width: 100%;
        height: auto;
    }

    #reuse-msg, #overwrite-msg {
        width: 1fr;
        height: auto;
        text-align: center;
        padding: 0 1;
    }

    #button-container {
        width: 100%;
        height: auto;
        align: center middle;
        margin: 1 0 2 0;
        padding: 0;
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

                    # Database info
                    yield Static("", id="db-info")

                    # Filters side-by-side
                    with Vertical(id="filters-container"):
                        with Vertical(id="filters-box"):
                            with Horizontal(id="filters-columns"):
                                with Center(id="previous-filters"):
                                    yield Static(
                                        "",
                                        id="previous-content",
                                        classes="filter-content"
                                    )
                                with Center(id="current-filters"):
                                    yield Static(
                                        "",
                                        id="current-content",
                                        classes="filter-content"
                                    )

                    # Explanation messages side-by-side
                    with Horizontal(id="message-columns"):
                        yield Static(
                            "[#3f9c35]Reuse[/#3f9c35]: "
                            "Keep existing data and filters",
                            id="reuse-msg"
                        )
                        yield Static(
                            "[#c9190b]Overwrite[/#c9190b]: "
                            "Delete and rebuild using new filters",
                            id="overwrite-msg"
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

                    # Spacer before footer
                    yield Static("", id="spacer")

        yield Footer()

    def on_mount(self) -> None:
        """Load and display previous and current filters when mounted."""
        self._load_db_info()
        self._load_filters()
        # Focus on Reuse button by default
        self.query_one("#reuse-btn", Button).focus()

    def _load_db_info(self) -> None:
        """Load and display database path with colored text."""
        from rich.text import Text

        db_widget = self.query_one("#db-info", Static)
        rel_path = os.path.relpath(self.conf.dbfile, self.conf.cwd)

        text = Text()
        text.append("Database Already Exists: ", style=COLORS["warning"])
        text.append(rel_path, style=STYLES["value"])

        db_widget.update(text)

    def _load_filters(self) -> None:
        """Load and display previous and current filters."""
        from rich.text import Text

        prev_widget = self.query_one("#previous-content", Static)
        curr_widget = self.query_one("#current-content", Static)

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

        # Build previous filters text
        prev_text = Text()
        prev_text.append("Previous Filters:\n", style=COLORS["success"])
        if previous_filters:
            for f in previous_filters:
                prev_text.append(f"  • {f}\n")
        else:
            prev_text.append(
                "  No filter information available",
                style=STYLES["dim"]
            )

        # Build current filters text
        curr_text = Text()
        curr_text.append("New Filters:\n", style=COLORS["error"])
        if current_filters:
            for f in current_filters:
                curr_text.append(f"  • {f}\n")
        else:
            curr_text.append(
                "  No filters (showing all tasks)",
                style=STYLES["dim"]
            )

        prev_widget.update(prev_text)
        curr_widget.update(curr_text)

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
