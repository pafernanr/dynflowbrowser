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
        # Don't open DB yet - wait until user decides to reuse or create
        self.db = None

    def write(self, sqlite=None, postgres=None, input_dynflow=None):
        """Launch interactive Textual TUI application.

        This is a blocking call that runs until the user quits the TUI.

        Args:
            sqlite: OutputSQLite instance for data import (SQLite mode)
            postgres: InputPostgres instance (PostgreSQL mode)
            input_dynflow: InputDynflow instance for reading CSV files (SQLite mode)
        """
        app = DynflowTUI(
            self.db,
            self.conf,
            show_welcome=True,
            initial_mode="welcome",
            sqlite=sqlite,
            postgres=postgres,
            input_dynflow=input_dynflow
        )
        app.run()

    def write_tasks(self):
        """Not used in TUI mode - handled by interactive app."""
        pass

    def write_actions(self):
        """Not used in TUI mode - handled by interactive app."""
        pass
