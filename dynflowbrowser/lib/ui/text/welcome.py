"""Welcome screen for text UI."""
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

from .theme import STYLES
from .widgets import LogoBanner


class WelcomeScreen(Screen):
    """Welcome screen with interface selection."""

    BINDINGS = [
        Binding("q", "request_quit", "Quit", priority=True),
        Binding("escape", "request_quit", "Quit", show=True),
        Binding("t", "start_text", "Text"),
        Binding("h", "start_httpd", "Httpd"),
        Binding("left", "previous_button", "", show=False),
        Binding("right", "next_button", "", show=False),
    ]

    CSS = """
    WelcomeScreen {
        background: $surface;
    }

    #main-content {
        align: center middle;
        height: 1fr;
    }

    LogoBanner {
        margin: 0;
    }

    #spacer-1, #spacer-2 {
        height: 1;
    }

    #mode-label {
        width: 100%;
        text-align: center;
        margin: 0;
    }

    #mode-label.blink {
        text-style: blink;
    }

    #button-container {
        width: 100%;
        height: auto;
        align: center middle;
        margin: 1 0;
    }

    Button {
        width: 30;
        height: 3;
        margin: 0 2;
    }

    Button:focus {
        text-style: bold reverse;
    }

    #server-status {
        width: 100%;
        height: auto;
        min-height: 1;
        text-align: center;
        margin: 0;
    }

    #bottom-info {
        dock: bottom;
        height: 3;
        width: 100%;
        background: $surface;
        padding: 0 0 1 0;
    }

    #exec-args {
        width: 100%;
        height: 1;
        text-align: center;
        margin: 0;
        padding: 0;
        color: $text-muted;
    }

    #import-stats {
        width: 100%;
        height: 1;
        text-align: center;
        margin: 0;
        padding: 0;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the welcome screen."""
        with Center(id="main-content"):
            with Middle():
                with Vertical():
                    yield LogoBanner()
                    yield Static("", id="spacer-1")
                    yield Static("", id="spacer-2")
                    yield Static(
                        "Choose how to browse",
                        id="mode-label"
                    )
                    with Center():
                        with Horizontal(id="button-container"):
                            yield Button(
                                "Terminal Browser",
                                id="terminal-btn"
                            )
                            yield Button(
                                "HTTPD Service",
                                id="httpd-btn"
                            )
                    yield Static("", id="server-status")

        # Bottom info lines - docked at bottom
        with Vertical(id="bottom-info"):
            yield Static("", id="exec-args")
            yield Static("", id="import-stats")

        yield Footer()

    def on_mount(self) -> None:
        """Set focus on first button when screen mounts."""
        self.query_one("#terminal-btn", Button).focus()

    def on_show(self) -> None:
        """Called when screen becomes visible."""
        # Update httpd button status each time screen is shown
        self.update_httpd_button_status()

    def update_httpd_button_status(self) -> None:
        """Update httpd button to show if server is running."""
        try:
            status_widget = self.query_one("#server-status", Static)
            # Check if httpd server is already started
            if (hasattr(self.app, 'httpd_server') and
                    self.app.httpd_server is not None):
                # Server is running - show status
                status_widget.update(
                    "[bold green]✓ HTTP Server is running[/bold green]"
                )
            else:
                # Server not running - show stopped status
                status_widget.update(
                    "[bold red]✗ HTTP Server is stopped[/bold red]"
                )
        except Exception as e:
            # Widget not found or other error - try to show error
            try:
                status_widget = self.query_one("#server-status", Static)
                status_widget.update(f"[red]Error: {e}[/red]")
            except Exception:
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "terminal-btn":
            self.app.action_switch_mode("tasks")
        elif event.button.id == "httpd-btn":
            self.app.action_switch_mode("httpd")

    def action_start_text(self) -> None:
        """Start terminal interface."""
        self.app.action_switch_mode("tasks")

    def action_start_httpd(self) -> None:
        """Start HTTP server."""
        self.app.action_switch_mode("httpd")

    def action_previous_button(self) -> None:
        """Focus previous button."""
        self.screen.focus_previous()

    def action_next_button(self) -> None:
        """Focus next button."""
        self.screen.focus_next()

    def action_request_quit(self) -> None:
        """Request quit confirmation."""
        self.app.action_request_quit()

    def update_import_stats(self, stats: dict) -> None:
        """Update the import statistics display.

        Args:
            stats: Dictionary with import statistics per data type
        """
        try:
            stats_widget = self.query_one("#import-stats", Static)
            if stats:
                from rich.text import Text
                text = Text()
                text.append("Dynflow Data: ", style=STYLES["dim"])
                parts = []
                for dtype in ['tasks', 'plans', 'actions', 'steps']:
                    if dtype in stats:
                        s = stats[dtype]
                        parts.append(f"{s['rows']} {dtype}")
                text.append(" | ".join(parts), style=STYLES["success_text"])
                stats_widget.update(text)
        except Exception:
            pass

    def update_exec_args(self, argsfile: str) -> None:
        """Update the execution arguments display.

        Args:
            argsfile: Path to execution arguments file
        """
        try:
            from rich.text import Text

            args_widget = self.query_one("#exec-args", Static)
            if not os.path.exists(argsfile):
                return

            with open(argsfile, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Extract filter lines
            filters = []
            in_filters = False
            for line in lines:
                line = line.strip()
                if line.startswith("Filters:"):
                    in_filters = True
                    # Check if "None" is in the same line
                    if "None" in line:
                        filters.append("No filters")
                        break
                elif in_filters and line.startswith("-"):
                    filters.append(line[2:].strip())  # Remove "- " prefix
                elif in_filters and line and not line.startswith("-"):
                    break

            if filters:
                text = Text()
                text.append("Filters: ", style=STYLES["dim"])
                text.append(" | ".join(filters), style=STYLES["subtitle"])
                args_widget.update(text)
        except Exception:
            # Silently fail
            pass
