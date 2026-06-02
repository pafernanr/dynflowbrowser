"""Database reuse confirmation modal for TUI."""
import os

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center
from textual.containers import Horizontal
from textual.containers import Vertical
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button
from textual.widgets import Static


class DatabaseReuseModal(ModalScreen):
    """Modal to confirm database reuse or overwrite."""

    BINDINGS = [
        Binding("q", "request_quit", "Quit", priority=True),
        Binding("escape", "request_quit", "Quit", show=True),
        Binding("left", "previous_button", "", show=False),
        Binding("right", "next_button", "", show=False),
    ]

    CSS = """
    DatabaseReuseModal {
        align: center middle;
    }

    #dialog {
        width: 80;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    #title {
        width: 100%;
        text-align: center;
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }

    #db-path {
        width: 100%;
        text-align: center;
        margin-bottom: 1;
        color: $text-muted;
    }

    #filters-section {
        width: 100%;
        height: auto;
        max-height: 15;
        margin: 1 0;
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
        margin: 1 0;
    }

    #button-container {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 1;
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
        """Compose the modal dialog."""
        with Vertical(id="dialog"):
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
                "[#ec7a08]Overwrite[/#ec7a08]: Delete and rebuild "
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
                        variant="warning",
                        id="overwrite-btn"
                    )

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
        text.append("Previous Filters:\n", style="bold #3f9c35")
        if previous_filters:
            for f in previous_filters:
                text.append(f"  • {f}\n")
        else:
            text.append("  No filter information available\n", style="dim")

        # Display current filters
        text.append("Current Filters:\n", style="bold #ec7a08")
        if current_filters:
            for i, f in enumerate(current_filters):
                if i < len(current_filters) - 1:
                    text.append(f"  • {f}\n")
                else:
                    text.append(f"  • {f}")
        else:
            text.append("  No filters (showing all tasks)", style="dim")

        filters_widget.update(text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "reuse-btn":
            self.dismiss(True)  # Reuse = True
        elif event.button.id == "overwrite-btn":
            self.dismiss(False)  # Reuse = False

    def action_previous_button(self) -> None:
        """Focus previous button."""
        self.screen.focus_previous()

    def action_next_button(self) -> None:
        """Focus next button."""
        self.screen.focus_next()

    def action_request_quit(self) -> None:
        """Request quit confirmation."""
        self.app.action_request_quit()
