"""Textual TUI application for browsing Dynflow data."""
from textual.app import App
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.screen import Screen
from textual.widgets import Button
from textual.widgets import Footer
from textual.widgets import Header
from textual.widgets import Static

from .httpd_info import HttpdInfoScreen
from .welcome import WelcomeScreen
from .widgets import HeaderSeparator
from .widgets import HostDetailsHeader
from .widgets import StatsPanel
from .widgets import TasksDataTable


class TasksScreen(Screen):
    """Main screen showing tasks list."""

    BINDINGS = [
        Binding("q", "app.quit", "Quit", priority=True),
        Binding("escape", "back_to_welcome", "Back", show=True),
        Binding("h", "show_httpd_modal", "HTTP Access", show=True,
                key_display="│ h"),
        Binding("s", "toggle_stats", "Dynflow/Pulp Stats", show=True),
        Binding("t", "toggle_columns", "View Foreman/Dynflow", show=True,
                key_display="│ t"),
        Binding("d", "app.toggle_dark", "Dark Mode", show=False),
    ]

    def __init__(self, db, conf, show_welcome=False):
        """Initialize tasks screen.

        Args:
            db: OutputSQLite database instance
            conf: Configuration object
            show_welcome: If True, ESC goes to welcome screen
        """
        super().__init__()
        self.db = db
        self.conf = conf
        self.stats_visible = False
        self.show_welcome = show_welcome

    def on_data_table_row_selected(self, event) -> None:
        """Handle row selection in the tasks table (Enter key).

        Args:
            event: The row selected event
        """
        self.action_view_actions()

    def on_key(self, event) -> None:
        """Handle key presses for navigation.

        Args:
            event: The key event
        """
        table = self.query_one(TasksDataTable)

        # Only Enter navigates to actions
        if event.key == "enter":
            if table.cursor_row is not None:
                self.action_view_actions()
                event.prevent_default()
                event.stop()
        # Left/Right now scroll horizontally (default DataTable behavior)

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header(show_clock=False)
        version = self.conf.sos.get('version', '0')
        yield HeaderSeparator(version)

        # Stats panel (initially hidden) - expands below separator
        yield StatsPanel(
            self.db, self.conf, id="stats_panel", classes="hidden"
        )

        yield HostDetailsHeader(self.conf.sos)

        # Tasks table
        yield TasksDataTable(
            self.db,
            self.conf,
            id="tasks_table"
        )

        yield Footer()

    def on_mount(self) -> None:
        """Focus the table when screen is mounted."""
        table = self.query_one(TasksDataTable)
        table.focus()

    def action_back_to_welcome(self) -> None:
        """Go back to welcome screen or quit."""
        if self.show_welcome:
            self.app.action_switch_mode("welcome")
        else:
            self.app.action_quit()

    def action_toggle_columns(self) -> None:
        """Toggle between Action/ID and Label/Plan UUID."""
        table = self.query_one(TasksDataTable)
        table.toggle_columns()

    def action_toggle_stats(self) -> None:
        """Toggle the stats panel visibility."""
        stats_panel = self.query_one("#stats_panel")
        if self.stats_visible:
            stats_panel.add_class("hidden")
            self.stats_visible = False
        else:
            stats_panel.remove_class("hidden")
            self.stats_visible = True

    def action_view_actions(self) -> None:
        """View actions for the selected task."""
        table = self.query_one(TasksDataTable)

        # Get the row key for the current cursor position
        if table.cursor_row is None or table.cursor_row >= len(table.row_keys):
            return

        row_key = table.row_keys[table.cursor_row]

        # Only navigate if this is a parent task
        if row_key in table.row_to_plan:
            plan_uuid = table.row_to_plan[row_key]
            self.app.push_screen(
                ActionsScreen(self.db, self.conf, plan_uuid)
            )

    def action_show_httpd_modal(self) -> None:
        """Show HTTP server access modal."""
        self.app.push_screen(HttpdAccessModal(self.conf, plan_uuid=None))


class ActionsScreen(Screen):
    """Screen showing actions and steps for a specific task/plan."""

    # All bindings with visual separators
    BINDINGS = [
        Binding("q", "app.quit", "Quit", priority=True),
        Binding("escape", "app.pop_screen", "Back", show=True),
        Binding("h", "show_httpd_modal", "HTTP Access", show=True,
                key_display="│ h"),
        Binding("s", "toggle_stats", "Dynflow/Pulp Stats", show=True),
        Binding("d", "show_detail_menu", "Details", show=True,
                key_display="│ d"),
    ]

    def __init__(self, db, conf, plan_uuid):
        """Initialize actions screen.

        Args:
            db: OutputSQLite database instance
            conf: Configuration object
            plan_uuid: The execution plan UUID to show actions for
        """
        super().__init__()
        self.db = db
        self.conf = conf
        self.plan_uuid = plan_uuid
        self.stats_visible = False
        self.detail_visible = None
        self.current_row_type = None

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header(show_clock=False)
        version = self.conf.sos.get('version', '0')
        yield HeaderSeparator(version)

        # Stats panel (initially hidden) - expands below separator
        from .widgets import ActionStatsPanel
        yield ActionStatsPanel(
            self.db,
            self.conf,
            self.plan_uuid,
            id="action_stats_panel",
            classes="hidden"
        )

        # Action details header (Task, Label, ID, Caller, Plan)
        from .widgets import ActionDetailsHeader
        yield ActionDetailsHeader(self.db, self.plan_uuid, id="action_details")

        # Actions tree view
        from .widgets import ActionsTreeTable
        yield ActionsTreeTable(
            self.db,
            self.conf,
            plan_uuid=self.plan_uuid,
            id="actions_tree"
        )

        yield Footer()

    def action_toggle_stats(self) -> None:
        """Toggle the stats panel visibility."""
        stats_panel = self.query_one("#action_stats_panel")
        if self.stats_visible:
            stats_panel.add_class("hidden")
            self.stats_visible = False
        else:
            stats_panel.remove_class("hidden")
            self.stats_visible = True

    def action_expand_action(self) -> None:
        """Expand current action to show steps."""
        table = self.query_one("#actions_tree")
        if hasattr(table, 'expand_action'):
            table.expand_action()

    def action_collapse_action(self) -> None:
        """Collapse current action to hide steps."""
        table = self.query_one("#actions_tree")
        if hasattr(table, 'collapse_action'):
            table.collapse_action()

    def action_show_detail_menu(self) -> None:
        """Show detail menu for current row."""
        table = self.query_one("#actions_tree")

        # Get current row info
        if table.cursor_row is None or table.cursor_row >= len(table.row_keys):
            return

        row_key = table.row_keys[table.cursor_row]

        # Get row data to check for alerts
        row_data = table.row_data.get(row_key)
        if not row_data:
            return

        # Determine row type and available options
        if row_key.startswith('action_'):
            action_data = row_data['data']
            # Check output field (index 7) for alert
            output = action_data[7] if len(action_data) > 7 else ""
            has_output_alert = output and output != "{}"

            options = [
                ("Input", "input", False),
                ("Output", "output", has_output_alert),
                ("Data", "data", False),
            ]
            title = "Action Details"
        elif row_key.startswith('step_'):
            step_data = row_data['data']
            # Check error field (index 13) for alert
            error = step_data[13] if len(step_data) > 13 else ""
            has_error_alert = bool(error)

            options = [
                ("Error", "error", has_error_alert),
                ("Queue", "queue", False),
                ("Children", "children", False),
                ("Data", "data", False),
            ]
            title = "Step Details"
        else:
            return

        # Show detail menu modal
        self.app.push_screen(
            DetailMenuModal(title, options, table, row_key)
        )

    def on_mount(self) -> None:
        """Setup when screen is mounted."""
        table = self.query_one("#actions_tree")
        table.focus()

    def on_key(self, event) -> None:
        """Handle key presses.

        Args:
            event: The key event
        """
        table = self.query_one("#actions_tree")

        # Enter expands/collapses nodes
        if event.key == "enter":
            if table.cursor_row is None or table.cursor_row >= len(table.row_keys):
                return

            row_key = table.row_keys[table.cursor_row]
            if row_key not in table.row_data:
                return

            row_data = table.row_data[row_key]

            # Only expand/collapse actions (not steps)
            if row_data['type'] == 'action':
                action_id = row_data['action_id']
                # Toggle expansion
                if action_id in table.expanded_actions:
                    table.collapse_action()
                else:
                    table.expand_action()
                event.prevent_default()
                event.stop()
        # Left/Right now scroll horizontally (default DataTable behavior)

    def update_bindings(self, row_type: str = None) -> None:
        """Update current row type for validation.

        Args:
            row_type: 'action' or 'step' or None
        """
        self.current_row_type = row_type

    def action_show_httpd_modal(self) -> None:
        """Show HTTP server access modal."""
        self.app.push_screen(
            HttpdAccessModal(self.conf, plan_uuid=self.plan_uuid)
        )


class HttpdAccessModal(ModalScreen):
    """Modal to show HTTP server access info or start the server."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=True),
        Binding("q", "dismiss", "Close", show=False),
        Binding("y", "start_server", "Yes", show=False),
        Binding("n", "dismiss", "No", show=False),
    ]

    def __init__(self, conf, plan_uuid=None, **kwargs):
        """Initialize HTTP access modal.

        Args:
            conf: Configuration object
            plan_uuid: Optional plan UUID for actions screen
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)
        self.conf = conf
        self.plan_uuid = plan_uuid
        self.server_started = False

    def compose(self) -> ComposeResult:
        """Create modal widgets."""
        from textual.containers import Container
        from textual.containers import VerticalScroll

        with Container(id="httpd_modal_container"):
            yield Static("HTTP Server Access", id="httpd_modal_title")
            yield VerticalScroll(id="httpd_modal_content")

    def on_mount(self) -> None:
        """Setup initial content when modal is mounted."""
        self._update_content()

    def _update_content(self) -> None:
        """Update modal content based on server state."""
        content_area = self.query_one("#httpd_modal_content")
        content_area.remove_children()

        # Check if server is running
        server_running = (
            hasattr(self.app, 'httpd_server')
            and self.app.httpd_server is not None
        )

        if server_running:
            # Server is running - show access information
            self._show_access_info(content_area)
        else:
            # Server is stopped - ask to start
            self._show_start_prompt(content_area)

    def _show_start_prompt(self, container) -> None:
        """Show prompt to start the server.

        Args:
            container: Container to add widgets to
        """
        from rich.text import Text

        prompt_text = Text()
        prompt_text.append(
            "The HTTP server is currently stopped.\n\n",
            style="dim"
        )
        prompt_text.append(
            "Would you like to start it?\n\n",
            style="bold"
        )
        prompt_text.append(
            "Press ",
            style="dim"
        )
        prompt_text.append("(y)", style="bold green")
        prompt_text.append(" for Yes or ", style="dim")
        prompt_text.append("(n)", style="bold red")
        prompt_text.append(" for No", style="dim")

        container.mount(Static(prompt_text))

    def _show_access_info(self, container) -> None:
        """Show server access information.

        Args:
            container: Container to add widgets to
        """
        from rich.text import Text

        if not hasattr(self.app, 'httpd_server') or not self.app.httpd_server:
            return

        # Build URL path based on plan_uuid
        url_path = f"/?plan_uuid={self.plan_uuid}" if self.plan_uuid else "/"

        # Direct HTTP Access section
        direct_text = Text()
        direct_text.append("Direct HTTP Access:\n", style="bold cyan")
        direct_lines = self.app.httpd_server.get_direct_access_lines(url_path)
        for line in direct_lines:
            direct_text.append(f"{line}\n", style="bold")

        container.mount(Static(direct_text))
        container.mount(Static(""))

        # SSH Tunnel Access section
        ssh_text = Text()
        ssh_text.append("SSH Tunnel Access:\n", style="bold cyan")
        ssh_lines = self.app.httpd_server.get_ssh_tunnel_lines(url_path)
        for line in ssh_lines:
            ssh_text.append(f"{line}\n", style="dim")

        container.mount(Static(ssh_text))

    def action_start_server(self) -> None:
        """Start the HTTP server."""
        from dynflowbrowser.lib.ui.httpd.output import HttpdOutput
        from dynflowbrowser.lib.ui.httpd.server import DynamicHttpServer
        import threading
        import time

        # Don't start if already running
        if hasattr(self.app, 'httpd_server') and self.app.httpd_server:
            self._update_content()
            return

        # Show starting message
        content_area = self.query_one("#httpd_modal_content")
        content_area.remove_children()
        content_area.mount(
            Static("[bold green]Starting HTTP Server...[/bold green]")
        )

        # Compute stats
        httpd_output = HttpdOutput(self.conf)
        pulp_stats, dynflow_stats = httpd_output.compute_execution_stats()
        httpd_output.copy_static_assets()

        # Create and start server
        self.app.httpd_server = DynamicHttpServer(
            self.conf,
            pulp_stats,
            dynflow_stats,
            quiet=True
        )

        def start_server():
            self.app.httpd_server.start()

        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        time.sleep(0.3)

        self.server_started = True

        # Update content to show access info
        self._update_content()

    def action_dismiss(self) -> None:
        """Close the modal."""
        self.app.pop_screen()


class DetailMenuModal(ModalScreen):
    """Modal screen to show detail menu options."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=True),
        Binding("q", "dismiss", "Close", show=False),
        Binding("1", "select(0)", "1", show=False),
        Binding("2", "select(1)", "2", show=False),
        Binding("3", "select(2)", "3", show=False),
        Binding("4", "select(3)", "4", show=False),
    ]

    def __init__(
            self,
            title: str,
            options: list,
            table,
            row_key: str,
            **kwargs
    ):
        """Initialize detail menu modal.

        Args:
            title: Title for the modal
            options: List of (label, detail_type, has_alert) tuples
            table: Reference to the ActionsTreeTable
            row_key: The current row key
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)
        self.title_text = title
        self.options = options
        self.table = table
        self.row_key = row_key
        self.selected_index = 0

    def compose(self) -> ComposeResult:
        """Create modal widgets."""
        from rich.text import Text
        from textual.containers import Container
        with Container(id="menu_container"):
            yield Static(self.title_text, id="menu_title")
            for idx, option_tuple in enumerate(self.options):
                label = option_tuple[0]
                has_alert = option_tuple[2] if len(option_tuple) > 2 else False

                # Build menu text with alert indicator
                menu_text = Text()
                menu_text.append(f"{idx + 1}. {label}")
                if has_alert:
                    menu_text.append(" !", style="bold red")

                style = "reverse" if idx == self.selected_index else ""
                yield Static(
                    menu_text,
                    id=f"menu_item_{idx}",
                    classes=style
                )

    def on_key(self, event) -> None:
        """Handle key presses for menu navigation."""
        if event.key == "up":
            self.selected_index = (self.selected_index - 1) % len(self.options)
            self.refresh_menu()
            event.prevent_default()
        elif event.key == "down":
            self.selected_index = (self.selected_index + 1) % len(self.options)
            self.refresh_menu()
            event.prevent_default()
        elif event.key == "enter":
            self.action_select(self.selected_index)
            event.prevent_default()

    def refresh_menu(self) -> None:
        """Refresh menu item styles based on selection."""
        from rich.text import Text
        for idx in range(len(self.options)):
            label = self.options[idx][0]
            has_alert = (
                self.options[idx][2] if len(self.options[idx]) > 2 else False
            )

            # Rebuild text with alert
            menu_text = Text()
            menu_text.append(f"{idx + 1}. {label}")
            if has_alert:
                menu_text.append(" !", style="bold red")

            item = self.query_one(f"#menu_item_{idx}")
            item.update(menu_text)

            if idx == self.selected_index:
                item.add_class("reverse")
            else:
                item.remove_class("reverse")

    def action_select(self, index: int) -> None:
        """Select a menu item and show its detail.

        Args:
            index: Index of selected option
        """
        if 0 <= index < len(self.options):
            detail_type = self.options[index][1]
            self.app.pop_screen()
            if hasattr(self.table, 'toggle_detail'):
                self.table.toggle_detail(detail_type)

    def action_dismiss(self) -> None:
        """Close the modal."""
        self.app.pop_screen()


class QuitModal(ModalScreen):
    """Modal screen for quit confirmation."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("left", "previous_button", "", show=False),
        Binding("right", "next_button", "", show=False),
        Binding("enter", "select", "Select", show=True),
    ]

    def compose(self) -> ComposeResult:
        """Compose the quit confirmation modal."""
        from textual.containers import Container
        with Container(id="quit_container"):
            yield Static("Quit DynflowBrowser?", id="quit_title")
            with Container(id="quit_content"):
                with Horizontal(id="quit_buttons"):
                    yield Button("Yes", id="quit_yes", variant="error")
                    yield Button("No", id="quit_no", variant="primary")

    def on_mount(self) -> None:
        """Focus the Yes button when modal opens."""
        self.query_one("#quit_yes", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "quit_yes":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        """Cancel quit."""
        self.dismiss(False)

    def action_select(self) -> None:
        """Select focused button."""
        focused = self.focused
        if isinstance(focused, Button):
            focused.press()

    def action_previous_button(self) -> None:
        """Focus previous button."""
        self.focus_previous()

    def action_next_button(self) -> None:
        """Focus next button."""
        self.focus_next()


class AboutModal(ModalScreen):
    """Modal screen to display project information."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=True),
        Binding("q", "dismiss", "Close", show=False),
    ]

    def __init__(self, version: str = "0", **kwargs):
        """Initialize about modal.

        Args:
            version: Project version
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)
        self.version = version

    def compose(self) -> ComposeResult:
        """Create modal widgets."""
        from textual.containers import Container
        with Container(id="about_container"):
            yield Static("About DynflowBrowser", id="about_title")

            content = (
                f"[bold cyan]DynflowBrowser[/bold cyan] "
                f"[dim]{self.version}[/dim]\n\n"
                "[dim]Browse and analyze Dynflow execution data from "
                "Red Hat Satellite sosreports.[/dim]\n\n"
                "[cyan]GitHub:[/cyan] "
                "https://github.com/pafernanr/dynflowbrowser\n"
            )
            yield Static(content, id="about_content")

    def action_dismiss(self) -> None:
        """Close the modal."""
        self.app.pop_screen()


class DetailModal(ModalScreen):
    """Modal screen to display JSON detail data."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=True),
        Binding("q", "dismiss", "Close", show=False),
    ]

    def __init__(self, title: str, content: str, **kwargs):
        """Initialize detail modal.

        Args:
            title: Title for the modal
            content: Content to display
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)
        self.title_text = title
        self.content_text = content

    def compose(self) -> ComposeResult:
        """Create modal widgets."""
        with VerticalScroll(id="detail_container"):
            yield Static(self.title_text, id="detail_title")
            yield Static(self.content_text, id="detail_content")

    def action_dismiss(self) -> None:
        """Close the modal."""
        self.app.pop_screen()


class DynflowTUI(App):
    """Interactive Textual TUI for browsing Dynflow tasks and actions."""

    CSS = """
    HeaderSeparator {
        height: 1;
        padding: 0;
    }

    HostDetailsHeader {
        height: 2;
        background: $boost;
        padding: 0;
    }

    #action_details {
        height: auto;
        background: $panel;
        padding: 0;
    }

    #stats_panel, #action_stats_panel {
        width: 100%;
        height: auto;
        border: solid $primary;
        padding: 0;
        background: $surface;
    }

    #stats_panel.hidden, #action_stats_panel.hidden {
        display: none;
    }

    #tasks_table, #actions_tree {
        height: 1fr;
    }

    DataTable {
        height: 1fr;
    }

    DataTable > .datatable--cursor {
        text-style: none;
    }

    DataTable > .datatable--hover {
        text-style: none;
    }

    .error {
        color: $error;
    }

    .success {
        color: $success;
    }

    .warning {
        color: $warning;
    }

    QuitModal {
        align: center middle;
    }

    #quit_container {
        width: 50;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 0;
    }

    #quit_title {
        background: $boost;
        color: $text;
        padding: 1;
        text-align: center;
        text-style: bold;
    }

    #quit_content {
        padding: 1;
        height: auto;
    }

    #quit_buttons {
        width: 100%;
        height: auto;
        align: center middle;
    }

    #quit_buttons Button {
        margin: 0 1;
    }

    AboutModal {
        align: center middle;
    }

    #about_container {
        width: 70;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 0;
    }

    #about_title {
        background: $boost;
        color: $text;
        padding: 0;
        text-style: bold;
    }

    #about_content {
        padding: 0;
        height: auto;
    }

    HttpdAccessModal {
        align: center middle;
    }

    #httpd_modal_container {
        width: 82;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 0;
    }

    #httpd_modal_title {
        background: $boost;
        color: $text;
        padding: 0;
        text-style: bold;
    }

    #httpd_modal_content {
        padding: 1;
        height: auto;
        max-height: 30;
    }

    DetailMenuModal {
        align: center middle;
    }

    #menu_container {
        width: 40;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 0;
    }

    #menu_title {
        background: $boost;
        color: $text;
        padding: 0;
        text-style: bold;
        dock: top;
    }

    #menu_container Static {
        padding: 0;
        height: 1;
    }

    .reverse {
        background: $primary;
        color: $text;
    }

    DetailModal {
        align: center middle;
    }

    #detail_container {
        width: 90%;
        height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 0;
    }

    #detail_title {
        background: $boost;
        color: $text;
        padding: 0;
        text-style: bold;
    }

    #detail_content {
        padding: 0;
        height: auto;
    }
    """

    TITLE = "DynflowBrowser"
    SUB_TITLE = ""

    MODES = {
        "welcome": WelcomeScreen,
        "tasks": TasksScreen,
        "httpd": HttpdInfoScreen,
    }

    def __init__(self, db, conf, show_welcome=False, initial_mode="welcome",
                 sqlite=None, input_dynflow=None):
        """Initialize the TUI application.

        Args:
            db: OutputSQLite database instance
            conf: Configuration object
            show_welcome: If True, show welcome screen first
            initial_mode: Initial mode to start with (welcome/tasks/httpd)
            sqlite: OutputSQLite instance for data import
            input_dynflow: InputDynflow instance for reading CSV files
        """
        super().__init__()
        self.db = db
        self.conf = conf
        self.show_welcome = show_welcome
        self.initial_mode = initial_mode
        self.httpd_server = None
        self.sqlite = sqlite
        self.input_dynflow = input_dynflow
        self.import_stats = None

    def on_mount(self) -> None:
        """Mount the initial screen."""
        # Install quit modal
        self.install_screen(QuitModal(), "quit")

        # If we need to import data, show loading screen first
        if self.conf.writesql and self.sqlite and self.input_dynflow:
            from .loading import LoadingScreen
            loading_screen = LoadingScreen()
            self.install_screen(loading_screen, "loading")
            self.push_screen("loading")
            # Start import in background worker
            self.run_worker(
                self._import_data_worker,
                name="import_data",
                exclusive=True,
                exit_on_error=False,
                thread=True
            )
        elif self.show_welcome:
            # Database was reused - count existing rows
            self._count_existing_data()
            # Show welcome screen with mode selection
            self.install_screen(WelcomeScreen(), "welcome")
            self.install_screen(
                TasksScreen(self.db, self.conf, show_welcome=True),
                "tasks"
            )
            self.push_screen("welcome")
            # Update welcome screen with stats
            if self.import_stats:
                self._update_welcome_stats()
        elif self.initial_mode == "httpd":
            # Start directly in httpd mode
            self._start_httpd_direct()
        else:
            # Go directly to tasks (no welcome to go back to)
            self.push_screen(
                TasksScreen(self.db, self.conf, show_welcome=False)
            )

    def action_switch_mode(self, mode: str) -> None:
        """Switch to a different mode.

        Args:
            mode: Mode name (welcome/tasks/httpd)
        """
        if mode == "httpd":
            # Start HTTP server and show info screen
            self.start_httpd_server()
        elif mode in self.MODES:
            self.switch_screen(mode)
            # If switching to welcome, update server status
            if mode == "welcome":
                try:
                    welcome_screen = self.get_screen("welcome")
                    welcome_screen.update_httpd_button_status()
                except Exception:
                    pass

    def _start_httpd_direct(self) -> None:
        """Start httpd server directly (when launched with --httpd flag)."""
        # Create and push httpd info screen (can't go back)
        # Server will be started manually with (s) key
        server_info = {}
        httpd_screen = HttpdInfoScreen(
            self.conf, server_info, can_go_back=False
        )
        self.push_screen(httpd_screen)

    def start_httpd_server(self) -> None:
        """Start HTTP server and display info screen."""
        # Check if httpd screen is already installed
        if "httpd" in self._installed_screens:
            # Just switch to existing screen
            self.switch_screen("httpd")
            return

        # Create httpd info screen (can go back to welcome)
        # Server will be started manually with (s) key
        server_info = {}
        httpd_screen = HttpdInfoScreen(
            self.conf, server_info, can_go_back=True
        )
        self.install_screen(httpd_screen, "httpd")

        # Switch to httpd screen
        self.switch_screen("httpd")

    def _import_data_worker(self) -> None:
        """Import CSV data into SQLite with progress updates (runs in worker thread)."""
        import time
        from dynflowbrowser.lib.outputsqlite import OutputSQLite

        stats = {}

        try:
            # Create SQLite connection in this worker thread
            sqlite_worker = OutputSQLite(self.conf)

            # Import each data type with progress
            for dtype in ['tasks', 'plans', 'actions', 'steps']:
                self.call_from_thread(
                    self._update_loading_status,
                    f"Reading {dtype}..."
                )
                dynflow = self.input_dynflow.read_dynflow(dtype)

                def progress_callback(current, total):
                    self.call_from_thread(
                        self._update_loading_progress,
                        dtype, current, total
                    )

                result = sqlite_worker.write(dtype, dynflow, progress_callback)
                stats[dtype] = result

            # Create indexes
            self.call_from_thread(
                self._update_loading_status,
                "Creating database indexes..."
            )
            self.call_from_thread(
                self._update_loading_progress,
                "indexes", 0, 100
            )
            sqlite_worker.create_indexes()
            self.call_from_thread(
                self._update_loading_progress,
                "indexes", 100, 100
            )

            # Close worker connection
            sqlite_worker.close()

            # Small delay to show completion
            time.sleep(0.5)

            # Store stats and switch to welcome screen
            self.import_stats = stats
            self.call_from_thread(self._switch_to_welcome)

        except Exception as e:
            import traceback
            error_msg = f"{e}\n{traceback.format_exc()}"
            self.call_from_thread(
                self._update_loading_status,
                f"[bold red]Error: {error_msg}[/bold red]"
            )
            time.sleep(5)
            # Still try to switch to welcome on error
            self.call_from_thread(self._switch_to_welcome)

    def _switch_to_welcome(self) -> None:
        """Switch to welcome screen after import completes."""
        # Switch to welcome screen
        self.install_screen(WelcomeScreen(), "welcome")
        self.install_screen(
            TasksScreen(self.db, self.conf, show_welcome=True),
            "tasks"
        )
        self.switch_screen("welcome")

        # Update welcome screen with stats
        if self.import_stats:
            self._update_welcome_stats()

    def _update_loading_status(self, message: str) -> None:
        """Update loading screen status message.

        Args:
            message: Status message to display
        """
        try:
            loading_screen = self.get_screen("loading")
            loading_screen.update_status(message)
        except Exception:
            pass

    def _update_loading_progress(self, dtype: str, current: int, total: int) -> None:
        """Update loading screen progress bar.

        Args:
            dtype: Data type (tasks, plans, actions, steps, indexes)
            current: Current progress
            total: Total items
        """
        try:
            loading_screen = self.get_screen("loading")
            loading_screen.update_progress(dtype, current, total)
        except Exception:
            pass

    def _update_welcome_stats(self) -> None:
        """Update welcome screen with import statistics."""
        try:
            welcome_screen = self.get_screen("welcome")
            welcome_screen.update_import_stats(self.import_stats)
            # Also update execution arguments
            welcome_screen.update_exec_args(self.conf.argsfile)
        except Exception:
            pass

    def _count_existing_data(self) -> None:
        """Count rows in existing database when reused."""
        try:
            stats = {}
            for dtype in ['tasks', 'plans', 'actions', 'steps']:
                count = self.db.query(f"SELECT COUNT(*) FROM {dtype}")[0][0]
                stats[dtype] = {
                    'dtype': dtype,
                    'rows': count,
                    'seconds': 0,
                    'speed': 0
                }
            self.import_stats = stats
        except Exception:
            pass

    def action_request_quit(self) -> None:
        """Show quit confirmation and exit if confirmed."""
        def check_quit(quit_confirmed: bool) -> None:
            """Exit if user confirmed quit."""
            if quit_confirmed:
                self.exit()

        self.push_screen(QuitModal(), check_quit)

    def action_quit(self) -> None:
        """Override default quit to show confirmation."""
        self.action_request_quit()
