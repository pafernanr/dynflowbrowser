"""HTTP server info screen for text UI."""
import time

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Footer
from textual.widgets import Header
from textual.widgets import RichLog
from textual.widgets import Static


class HttpdInfoScreen(Screen):
    """Screen showing HTTP server connection info and logs."""

    BINDINGS = [
        Binding("q", "app.quit", "Quit", priority=True),
        Binding("escape", "back", "Back", show=True),
        Binding("s", "toggle_server", "Start/Stop", show=True),
    ]

    CSS = """
    HttpdInfoScreen {
        background: $surface;
    }

    #info-container {
        height: 11;
        border: solid $primary;
        margin: 1;
    }

    #direct-access, #ssh-tunnel {
        width: 50%;
        height: 100%;
        border-right: solid $primary;
        padding: 1 2;
    }

    #ssh-tunnel {
        border-right: none;
    }

    .info-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .info-line {
        margin: 0 0 0 2;
    }

    #server-status-msg {
        width: 100%;
        text-align: center;
        margin: 1 0 0 0;
    }

    #server-esc-tip {
        width: 100%;
        text-align: center;
        margin: 0 0 1 0;
    }

    #logs-container {
        height: 1fr;
        border: solid $primary;
        margin: 0 1 1 1;
    }

    #logs-title {
        width: 100%;
        text-style: bold;
        color: $accent;
        padding: 0 2;
        background: $primary-background;
    }

    #server-logs {
        width: 100%;
        height: 1fr;
        border: none;
        padding: 0 1;
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
        yield Header(show_clock=False)

        # Top section: Direct access | SSH tunnel
        with Container(id="info-container"):
            with Horizontal():
                # Direct access column
                with Container(id="direct-access"):
                    yield Static("Direct HTTP Access", classes="info-title")
                    yield Static(
                        "Server stopped",
                        classes="info-line",
                        id="direct-access-content"
                    )

                # SSH tunnel column
                with Container(id="ssh-tunnel"):
                    yield Static("SSH Tunnel Access", classes="info-title")
                    yield Static(
                        "Server stopped",
                        classes="info-line",
                        id="ssh-tunnel-content"
                    )

        # Status message between sections
        yield Static(
            "Press [bold cyan](s)[/bold cyan] to start the server",
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
        logs = self.query_one("#server-logs", RichLog)

        # Check if server was started externally before mount
        server_running = (
            hasattr(self.app, 'httpd_server')
            and self.app.httpd_server is not None
        )

        if server_running:
            self._sync_external_server()
        else:
            logs.write("[dim]HTTP Server ready. Press (s) to start.[/dim]")

    def on_show(self) -> None:
        """Called when screen becomes visible."""
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

        logs = self.query_one("#server-logs", RichLog)
        logs.write("[bold green]HTTP Server detected (started externally)[/bold green]")

        # Update server info
        self.server_info = {
            'ip_addresses': self.app.httpd_server.get_all_ips(),
            'port': self.app.httpd_server.port,
            'hostname': self.app.httpd_server.get_fqdn(),
        }
        self._update_display()
        self.server_running = True

        # Update status message
        status_msg = self.query_one("#server-status-msg", Static)
        status_msg.update(
            "Press [bold cyan](s)[/bold cyan] to stop the server"
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
            log_callback=log_callback
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
        }
        self._update_display()
        self.server_running = True

        # Update status message
        status_msg = self.query_one("#server-status-msg", Static)
        status_msg.update(
            "Press [bold cyan](s)[/bold cyan] to stop the server"
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

        # Clear connection info
        direct_content = self.query_one("#direct-access-content", Static)
        direct_content.update("Server stopped")
        ssh_content = self.query_one("#ssh-tunnel-content", Static)
        ssh_content.update("Server stopped")

        # Update status message
        status_msg = self.query_one("#server-status-msg", Static)
        status_msg.update(
            "Press [bold cyan](s)[/bold cyan] to start the server"
        )

        # Show stopped tip
        esc_tip = self.query_one("#server-esc-tip", Static)
        esc_tip.update("HTTPD is not required for Terminal Browser")

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
        # Update direct access content
        direct_content = self.query_one("#direct-access-content", Static)
        lines = []
        for iface, ip in self.server_info.get('ip_addresses', []):
            url = f"http://{ip}:{self.server_info['port']}/"
            if iface:
                lines.append(f"  {iface}: {url}")
            else:
                lines.append(f"  {url}")
        direct_content.update("\n".join(lines))

        # Update SSH tunnel content
        hostname = self.server_info.get('hostname', 'localhost')
        port = self.server_info.get('port', '8000')
        ssh_content = self.query_one("#ssh-tunnel-content", Static)
        ssh_lines = [
            "Create SSH tunnel:",
            f"  ssh -L {port}:localhost:{port} {hostname}",
            "",
            "Then open in browser:",
            f"  http://localhost:{port}/"
        ]
        ssh_content.update("\n".join(ssh_lines))

        # Update logs
        logs = self.query_one("#server-logs", RichLog)
        logs.write(
            "[bold green]HTTP Server started successfully[/bold green]"
        )
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
