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


class WelcomeScreen(Screen):
    """Welcome screen with interface selection."""

    BINDINGS = [
        Binding("q", "app.quit", "Quit", priority=True),
        Binding("t", "start_text", "Text"),
        Binding("h", "start_httpd", "Httpd"),
        Binding("left", "previous_button", "", show=False),
        Binding("right", "next_button", "", show=False),
    ]

    CSS = """
    WelcomeScreen {
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

    #mode-label {
        width: 100%;
        text-align: center;
        margin: 1 0;
    }

    #mode-label.blink {
        text-style: blink;
    }

    #button-container {
        width: 100%;
        height: auto;
        align: center middle;
        margin: 2 0;
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
        margin: 1 0 0 0;
    }

    #import-stats {
        width: 100%;
        height: auto;
        text-align: center;
        margin: 1 0 0 0;
        color: $text-muted;
    }
    """

    def __init__(self):
        """Initialize welcome screen."""
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
        """Compose the welcome screen."""
        # ASCII art for "DynFlowBrowser"
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
                        "Choose Your Browser:",
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
                text.append("Dynflow Data: ", style="dim")
                parts = []
                for dtype in ['tasks', 'plans', 'actions', 'steps']:
                    if dtype in stats:
                        s = stats[dtype]
                        parts.append(f"{s['rows']} {dtype}")
                text.append(" | ".join(parts), style="green")
                stats_widget.update(text)
        except Exception:
            pass
