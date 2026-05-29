"""Textual TUI application for browsing Dynflow data."""
from textual.app import App
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.screen import Screen
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
        Binding("s", "toggle_stats", "Stats", show=True),
        Binding("t", "toggle_columns", "Toggle Columns", show=True),
        Binding("left", "collapse_task", "Collapse", show=True),
        Binding("right", "expand_task", "Expand", show=True),
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
        """Handle key presses for navigation and expand/collapse.

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
        # Left/Right for expand/collapse
        elif event.key == "right":
            if hasattr(table, 'expand_task'):
                table.expand_task()
                event.prevent_default()
                event.stop()
        elif event.key == "left":
            if hasattr(table, 'collapse_task'):
                table.collapse_task()
                event.prevent_default()
                event.stop()

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header(show_clock=False)
        version = self.conf.sos.get('version', '0')
        yield HeaderSeparator(version)
        yield HostDetailsHeader(self.conf.sos)

        with Horizontal(id="main_content"):
            # Stats panel (initially hidden)
            yield StatsPanel(
                self.db, self.conf, id="stats_panel", classes="hidden"
            )

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

    def action_expand_task(self) -> None:
        """Expand current task to show children."""
        table = self.query_one(TasksDataTable)
        if hasattr(table, 'expand_task'):
            table.expand_task()

    def action_collapse_task(self) -> None:
        """Collapse current task to hide children."""
        table = self.query_one(TasksDataTable)
        if hasattr(table, 'collapse_task'):
            table.collapse_task()


class ActionsScreen(Screen):
    """Screen showing actions and steps for a specific task/plan."""

    # All bindings with visual separators
    BINDINGS = [
        Binding("q", "app.quit", "Quit", priority=True),
        Binding("escape", "app.pop_screen", "Back", show=True),
        # Stats group - separator (Textual adds space before automatically)
        Binding("s", "toggle_stats", "Stats", show=True,
                key_display="|  s"),
        Binding("left", "collapse_action", "◀", show=True),
        Binding("right", "expand_action", "▶", show=True),
        # Detail menu - separator
        Binding("enter", "show_detail_menu", "Details", show=True,
                key_display="|  enter"),
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

        # Action details header (Task, Label, ID, Caller, Plan)
        from .widgets import ActionDetailsHeader
        yield ActionDetailsHeader(self.db, self.plan_uuid, id="action_details")

        with Horizontal(id="actions_main"):
            # Stats panel (initially hidden)
            from .widgets import ActionStatsPanel
            yield ActionStatsPanel(
                self.db,
                self.conf,
                self.plan_uuid,
                id="action_stats_panel",
                classes="hidden"
            )

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
        if event.key == "enter":
            self.action_show_detail_menu()
            event.prevent_default()
            event.stop()

    def update_bindings(self, row_type: str = None) -> None:
        """Update current row type for validation.

        Args:
            row_type: 'action' or 'step' or None
        """
        self.current_row_type = row_type


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
        padding: 0 1;
    }

    HostDetailsHeader {
        height: 2;
        background: $boost;
        padding: 0 1;
    }

    #action_details {
        height: auto;
        background: $panel;
        padding: 0 1;
    }

    #main_content, #actions_main {
        height: 1fr;
    }

    #stats_panel, #action_stats_panel {
        width: auto;
        min-width: 50;
        max-width: 80;
        border: solid $primary;
        padding: 1;
        background: $surface;
    }

    #stats_panel.hidden, #action_stats_panel.hidden {
        display: none;
    }

    DataTable {
        height: 1fr;
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

    AboutModal {
        align: center middle;
    }

    #about_container {
        width: 70;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }

    #about_title {
        background: $boost;
        color: $text;
        padding: 1;
        text-style: bold;
    }

    #about_content {
        padding: 1;
        height: auto;
    }

    DetailMenuModal {
        align: center middle;
    }

    #menu_container {
        width: 40;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }

    #menu_title {
        background: $boost;
        color: $text;
        padding: 1;
        text-style: bold;
        dock: top;
    }

    #menu_container Static {
        padding: 0 1;
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
        padding: 1;
    }

    #detail_title {
        background: $boost;
        color: $text;
        padding: 1;
        text-style: bold;
    }

    #detail_content {
        padding: 1;
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

    def __init__(self, db, conf, show_welcome=False, initial_mode="welcome"):
        """Initialize the TUI application.

        Args:
            db: OutputSQLite database instance
            conf: Configuration object
            show_welcome: If True, show welcome screen first
            initial_mode: Initial mode to start with (welcome/tasks/httpd)
        """
        super().__init__()
        self.db = db
        self.conf = conf
        self.show_welcome = show_welcome
        self.initial_mode = initial_mode
        self.httpd_server = None

    def on_mount(self) -> None:
        """Mount the initial screen."""
        if self.show_welcome:
            # Show welcome screen with mode selection
            self.install_screen(WelcomeScreen(), "welcome")
            self.install_screen(
                TasksScreen(self.db, self.conf, show_welcome=True),
                "tasks"
            )
            self.push_screen("welcome")
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
