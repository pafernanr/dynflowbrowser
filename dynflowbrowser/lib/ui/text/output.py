"""Text UI output implementation using Textual framework."""
try:
    from textual.app import App
except ImportError:
    raise ImportError(
        "Textual is required for --text mode. Install with: pip install textual"
    )

from dynflowbrowser.lib.outputsqlite import OutputSQLite
from dynflowbrowser.lib.ui.base import BaseOutput
from .app import DynflowTUI


class TextOutput(BaseOutput):
    """Text UI output generator using Textual TUI framework."""

    def __init__(self, conf):
        """Initialize text output.

        Args:
            conf: Configuration object with args and settings
        """
        super().__init__(conf)
        self.db = OutputSQLite(conf)

    def write(self):
        """Launch interactive Textual TUI application.

        This is a blocking call that runs until the user quits the TUI.
        """
        # Determine initial mode
        if self.conf.args.httpd:
            # Start directly in httpd mode
            initial_mode = "httpd"
            show_welcome = False
        elif self.conf.args.text_ui:
            # Start directly in text/tasks mode
            initial_mode = "tasks"
            show_welcome = False
        else:
            # No explicit interface - show welcome screen
            initial_mode = "welcome"
            show_welcome = True

        app = DynflowTUI(
            self.db,
            self.conf,
            show_welcome=show_welcome,
            initial_mode=initial_mode
        )
        app.run()

    def write_tasks(self):
        """Not used in TUI mode - handled by interactive app."""
        pass

    def write_actions(self):
        """Not used in TUI mode - handled by interactive app."""
        pass
