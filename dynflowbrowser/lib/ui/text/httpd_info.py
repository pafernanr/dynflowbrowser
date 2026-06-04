"""HTTP server info screen for text UI."""
import time

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Footer
from textual.widgets import RichLog
from textual.widgets import Static

from .widgets import AppHeaderWithSeparator


class HttpdInfoScreen(Screen):
    """Screen showing HTTP server connection info and logs."""

    BINDINGS = [
        Binding("q", "app.quit", "Quit", priority=True),
        Binding("escape", "back", "Back", show=True),
        Binding("h", "toggle_server", "Start/Stop", show=True),
    ]

    CSS = """
    HttpdInfoScreen {
        background: $surface;
    }

    #http-access-container {
        height: auto;
        border: solid $primary;
        padding: 0;
        margin: 0;
    }

    #http-access-container HttpAccessInfo {
        height: auto;
        padding: 0;
    }

    #server-status-msg {
        width: 100%;
        text-align: center;
        margin: 1 0 0 0;
    }

    #server-esc-tip {
        width: 100%;
        text-align: center;
        margin: 0;
    }

    #logs-container {
        height: 1fr;
        border: solid $primary;
        margin: 1 0 0 0;
    }

    #logs-title {
        width: 100%;
        text-style: bold;
        color: $accent;
        padding: 0 1;
        background: $primary-background;
    }

    #server-logs {
        width: 100%;
        height: 1fr;
        border: none;
        padding: 0;
    }
    """

    def __init__(self, conf, server_info, can_go_back=True):
        """Initialize httpd info screen.

        Args:
            conf: Configuration object
            server_info: Dict with server connection details
            can_go_back: If True, ESC goes back; if False, ESC quits
        """
        super().__init__()
        self.conf = conf
        self.server_info = server_info
        self.server_thread = None
        self._mounted = False
        self.can_go_back = can_go_back
        self.server_running = False

    def compose(self) -> ComposeResult:
        """Compose the httpd info screen."""
        yield AppHeaderWithSeparator()

        # HTTP access info section (will be populated when server starts)
        yield Container(id="http-access-container")

        # Status message between sections
        yield Static(
            "Press [bold cyan](h)[/bold cyan] to start the server",
            id="server-status-msg"
        )
        yield Static(
            "HTTPD is not required for the Terminal Browser",
            id="server-esc-tip"
        )

        # Bottom section: Server logs
        with Container(id="logs-container"):
            yield Static("HTTP Server Logs", id="logs-title")
            yield RichLog(id="server-logs", highlight=True, markup=True)

        yield Footer()

    def on_mount(self) -> None:
        """Initialize when screen is mounted."""
        self._mounted = True

        # Check if server was started externally before mount
        server_running = (
            hasattr(self.app, 'httpd_server')
            and self.app.httpd_server is not None
        )

        if server_running:
            self._sync_external_server()

    def on_show(self) -> None:
        """Called when screen becomes visible."""
        self._check_server_state()

    def on_screen_resume(self) -> None:
        """Called when screen is resumed (Textual lifecycle hook)."""
        self._check_server_state()

    def _check_server_state(self) -> None:
        """Check and sync server state."""
        # Check global server state (in case it was started from modal)
        server_running = (
            hasattr(self.app, 'httpd_server')
            and self.app.httpd_server is not None
        )

        # If server was started externally, update our state
        if server_running and not self.server_running:
            self._sync_external_server()

        # Update tip message based on server state
        esc_tip = self.query_one("#server-esc-tip", Static)
        if self.server_running:
            esc_tip.update(
                "Press [bold cyan]ESC[/bold cyan] to use Terminal Browser "
                "(server keeps running)"
            )
        else:
            esc_tip.update("HTTPD is not required for Terminal Browser")

    def action_back(self) -> None:
        """Go back to welcome screen or quit."""
        if self.can_go_back:
            self.app.action_switch_mode("welcome")
        else:
            self.app.action_quit()

    def action_toggle_server(self) -> None:
        """Toggle HTTP server start/stop."""
        if self.server_running:
            self._stop_server()
        else:
            self._start_server()

    def _sync_external_server(self) -> None:
        """Sync state when server was started externally (e.g., from modal)."""
        if not hasattr(self.app, 'httpd_server') or not self.app.httpd_server:
            return

        # Update server info
        self.server_info = {
            'ip_addresses': self.app.httpd_server.get_all_ips(),
            'port': self.app.httpd_server.port,
            'hostname': self.app.httpd_server.get_fqdn(),
            'server': self.app.httpd_server,
        }
        self._update_display()
        self.server_running = True

        # Update status message
        status_msg = self.query_one("#server-status-msg", Static)
        status_msg.update(
            "Press [bold cyan](h)[/bold cyan] to stop the server"
        )

        # Show ESC tip
        esc_tip = self.query_one("#server-esc-tip", Static)
        esc_tip.update(
            "Press [bold cyan]ESC[/bold cyan] to use Terminal Browser "
            "(server keeps running)"
        )

    def _start_server(self) -> None:
        """Start the HTTP server."""
        from dynflowbrowser.lib.ui.httpd.output import HttpdOutput
        from dynflowbrowser.lib.ui.httpd.server import DynamicHttpServer
        import threading
        import time

        logs = self.query_one("#server-logs", RichLog)
        logs.write("[bold green]Starting HTTP Server...[/bold green]")

        # Compute stats
        httpd_output = HttpdOutput(self.conf)
        pulp_stats, dynflow_stats = httpd_output.compute_execution_stats()
        httpd_output.copy_static_assets()

        # Create server with log callback
        def log_callback(message):
            self.log_message(message)

        self.app.httpd_server = DynamicHttpServer(
            self.conf,
            pulp_stats,
            dynflow_stats,
            quiet=True,
            log_callback=log_callback,
            data_provider=httpd_output.data_provider
        )

        # Start server in background
        def start_server():
            self.app.httpd_server.start()

        self.server_thread = threading.Thread(
            target=start_server, daemon=True
        )
        self.server_thread.start()
        time.sleep(0.3)

        # Update server info
        self.server_info = {
            'ip_addresses': self.app.httpd_server.get_all_ips(),
            'port': self.app.httpd_server.port,
            'hostname': self.app.httpd_server.get_fqdn(),
            'server': self.app.httpd_server,
        }
        self._update_display()
        self.server_running = True

        # Update status message
        status_msg = self.query_one("#server-status-msg", Static)
        status_msg.update(
            "Press [bold cyan](h)[/bold cyan] to stop the server"
        )

        # Show ESC tip
        esc_tip = self.query_one("#server-esc-tip", Static)
        esc_tip.update(
            "Press [bold cyan]ESC[/bold cyan] to use Terminal Browser "
            "(server keeps running)"
        )

    def _stop_server(self) -> None:
        """Stop the HTTP server."""
        logs = self.query_one("#server-logs", RichLog)

        if self.app.httpd_server:
            logs.write("[bold red]Stopping HTTP Server...[/bold red]")
            try:
                self.app.httpd_server.stop()
                self.app.httpd_server = None
            except Exception as e:
                logs.write(f"[red]Error stopping server: {e}[/red]")

        self.server_running = False

        # Clear HTTP access container
        try:
            access_container = self.query_one(
                "#http-access-container", Container
            )
            access_container.remove_children()
        except Exception:
            pass

        # Update status message
        try:
            status_msg = self.query_one("#server-status-msg", Static)
            status_msg.update(
                "Press [bold cyan](h)[/bold cyan] to start the server"
            )
        except Exception:
            pass

        # Show stopped tip
        try:
            esc_tip = self.query_one("#server-esc-tip", Static)
            esc_tip.update("HTTPD is not required for Terminal Browser")
        except Exception:
            pass

        logs.write("[dim]HTTP Server stopped.[/dim]")

    def update_server_info(self, server_info):
        """Update server connection information.

        Args:
            server_info: Dict with updated server connection details
        """
        self.server_info = server_info

        if self._mounted:
            self._update_display()

    def _update_display(self):
        """Update the display with current server info."""
        from dynflowbrowser.lib.ui.text.widgets import HttpAccessInfo

        # Get the server instance
        server = self.server_info.get('server')

        if server:
            # Update HTTP access info using shared widget
            container = self.query_one("#http-access-container")
            container.remove_children()
            container.mount(HttpAccessInfo(server, url_path="/"))

        # Update logs
        logs = self.query_one("#server-logs", RichLog)
        logs.write(
            "[bold green]HTTP Server started successfully[/bold green]"
        )
        port = self.server_info.get('port', '8000')
        logs.write(f"[cyan]Listening on port {port}[/cyan]")

    def log_message(self, message: str) -> None:
        """Add a message to the server logs.

        Args:
            message: Log message to display
        """
        if not self._mounted:
            return

        logs = self.query_one("#server-logs", RichLog)
        timestamp = time.strftime("%H:%M:%S")
        logs.write(f"[dim]{timestamp}[/dim] {message}")
        # Auto-scroll to bottom
        logs.scroll_end(animate=False)
