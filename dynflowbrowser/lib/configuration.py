import argparse
import os

from dynflowbrowser.lib.util import Util


def get_version():
    """Get version string from __VERSION__ file.

    Returns:
        str: Version string (e.g., 'v0.0.1rc6')
    """
    fname = os.path.join(os.path.dirname(__file__), '..', '__VERSION__')
    try:
        with open(fname, encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "unknown"


class Conf:

    def __init__(self):
        self.cwd = os.getcwd()
        self.util = Util("W")
        self.dynflowdata = {
            'version': "0",
            'plans': {'times': 0},
            'steps': {'times': 0},
            'actions': {'times': 0},
            'includedUUID': [],
            }
        self.pulpcoredata = {
            'version': "0",
            'core_task': {'times': 0},
            'core_taskgroup': {'times': 0},
            'core_progressreport': {'times': 0},
            'core_groupprogressreport': {'times': 0}
            }
        self.writesql = True
        self.sos = {}
        self.dbfile = ""

        self.parser = argparse.ArgumentParser(
            description="Get sosreport dynflow files and generates user"
            + " friendly html pages for tasks, plans, actions and steps",
            epilog="""
Examples:
  # Combine state, result and time filters
  %(prog)s --state stopped --result error --task-days 10

  # Complex search query (AND / OR operators)
  %(prog)s --search="result != success" --task-days 3
  %(prog)s --search="label ~ Sync AND state = stopped AND result = error"
            """,
            formatter_class=argparse.RawDescriptionHelpFormatter
            )
        self.parser.add_argument(
            '-v',
            '--version',
            action='version',
            version=self.get_version(),
            )
        self.parser.add_argument(
            '--search',
            dest='search',
            help='Search query using foreman-rake syntax. '
                 'Supports operators: =, !=, ~, !~, >, <, >=, <= '
                 'and connectors: AND, OR',
            default=None
            )
        self.parser.add_argument(
            '--state',
            dest='state',
            help='Filter by task state. '
                 'Valid: paused, pending, planned, planning, running, stopped',
            choices=['paused', 'pending', 'planned',
                     'planning', 'running', 'stopped'],
            default=None
            )
        self.parser.add_argument(
            '--result',
            dest='result',
            help='Filter by task result. '
                 'Valid: error, pending, success, warning',
            choices=['error', 'pending', 'success', 'warning'],
            default=None
            )
        self.parser.add_argument(
            '--task-days',
            dest='task_days',
            help='Import only tasks from last N days. '
                 'Same as foreman-rake TASK_DAYS parameter.',
            type=int,
            default=None
            )
        self.parser.add_argument(
            '-o',
            '--output_path',
            help="Write output to this path. Default is './dynflowbrowser/'.",
            default=self.cwd,
            type=self.valid_output_path
            )
        self.parser.add_argument(
            'sosreport_path',
            help='Path to sos report folder. Default is current path.',
            nargs='?'
            )
        self.args = self.parser.parse_args()

        # Validate sosreport_path after parsing
        if self.args.sosreport_path is None:
            self.args.sosreport_path = self.cwd
        else:
            # Validate the provided path
            validated_path = self.valid_sosreport_path(
                self.args.sosreport_path
            )
            self.args.sosreport_path = validated_path

        # Backward compatibility: showall is True when no filters are specified
        self.args.showall = (
            self.args.search is None and
            self.args.state is None and
            self.args.result is None and
            self.args.task_days is None
        )

        self.set_sos_details()
        self.args.output_path = (
            f"{self.args.output_path}/dynflowbrowser/{self.sos['sosname']}"
            .replace('//', '/')
            )

        # Create base output directory
        os.makedirs(self.args.output_path, exist_ok=True)

        self.dbfile = self.args.output_path + "/dynflowbrowser.db"
        self.argsfile = self.args.output_path + "/execution_args.txt"

        # Check if database file already exists and ask user
        if os.path.exists(self.dbfile) and self.writesql:
            # Show relative path for cleaner output
            rel_path = os.path.relpath(self.dbfile, self.cwd)
            print(f"\nDatabase file already exists: {rel_path}")
            prompt = "Reuse existing database? [y/N]: "
            response = input(prompt).strip().lower()
            if response == 'y':
                # Reuse existing database, skip data import
                self.writesql = False
                print("Reusing existing database...")
            else:
                # Overwrite - remove old database files
                os.remove(self.dbfile)
                # Also remove WAL files if they exist
                for suffix in ['-wal', '-shm']:
                    wal_file = self.dbfile + suffix
                    if os.path.exists(wal_file):
                        os.remove(wal_file)
                print("Overwriting database...")
                # Also remove args file when overwriting
                if os.path.exists(self.argsfile):
                    os.remove(self.argsfile)

        # Save execution arguments to file only when creating new DB
        if self.writesql:
            self._save_execution_args()

    def _save_execution_args(self):
        """Save execution arguments to a file."""
        try:
            with open(self.argsfile, 'w', encoding='utf-8') as f:
                f.write("Execution Arguments:\n")
                f.write("===================\n\n")

                # Build filter description
                filters = []
                if self.args.search:
                    filters.append(f"Search: {self.args.search}")
                if self.args.state:
                    filters.append(f"State: {self.args.state}")
                if self.args.result:
                    filters.append(f"Result: {self.args.result}")
                if self.args.task_days:
                    filters.append(f"Task Days: {self.args.task_days}")

                if filters:
                    f.write("Filters:\n")
                    for filter_item in filters:
                        f.write(f"  - {filter_item}\n")
                else:
                    f.write("Filters: None (showing all tasks)\n")

                f.write(f"\nOutput Path: {self.args.output_path}\n")
                f.write(f"SOS Report: {self.args.sosreport_path}\n")
        except Exception:
            pass  # Silently ignore errors saving args file

    def get_version(self):
        """Get version and store in sos dict.

        Returns:
            str: Version string
        """
        version = get_version()
        self.sos['version'] = version
        return version

    def valid_output_path(self, path):
        if path[:1] == "/":
            fullpath = path
        else:
            fullpath = f"{self.cwd}/{path}"
        if os.path.exists(fullpath):
            return fullpath
        else:
            raise argparse.ArgumentTypeError(
                f"{fullpath!r} is not a valid path.")

    def valid_sosreport_path(self, path):
        # If it's current directory (default), just return it
        if path == self.cwd or path == '.':
            return path
        p = path + "/sos_commands/foreman/dynflow_schema_info"
        if os.path.exists(p):
            return path
        else:
            raise argparse.ArgumentTypeError(
                f"{p!r} doesn't exist.")


    def parse_ram_info(self, free_output):
        """Parse free command output and return memory/swap in GB."""
        try:
            lines = free_output.strip().split('\n')
            mem_total = 0
            swap_total = 0

            for line in lines:
                if line.startswith('Mem:'):
                    # Extract total memory (second column)
                    parts = line.split()
                    mem_total = int(parts[1])
                elif line.startswith('Swap:'):
                    # Extract total swap (second column)
                    parts = line.split()
                    swap_total = int(parts[1])

            # Convert to GB (assuming input is in KB)
            mem_gb = round(mem_total / 1024 / 1024, 1)
            swap_gb = round(swap_total / 1024 / 1024, 1)

            return f"Physical: {mem_gb}G / Swap: {swap_gb}G"
        except Exception:
            # If parsing fails, return a simple message
            return "N/A"

    def set_sos_details(self):
        self.sos['timezone'] = self.util.exec_command(
            f"grep 'Time zone:' {self.args.sosreport_path}/sos_commands/systemd/timedatectl"  # noqa E501
            + " | awk '{print $3}'").strip()
        self.sos['localtime'] = self.util.exec_command(
            f"grep 'Local time:' {self.args.sosreport_path}/sos_commands/systemd/timedatectl"  # noqa E501
            + " | awk '{print $4\" 23:59:59\"}'").strip()
        self.sos['hostname'] = self.util.exec_command(
            f"cat  {self.args.sosreport_path}/hostname").strip()
        ram_raw = self.util.exec_command(
            f"cat  {self.args.sosreport_path}/free")
        self.sos['ram'] = self.parse_ram_info(ram_raw)
        self.sos['cpu'] = self.util.exec_command(
            f"grep -e '^CPU(s)'  {self.args.sosreport_path}/sos_commands/processor/lscpu "  # noqa E501
            + " | awk '{print $2}'").strip()
        self.sos['tuning'] = self.util.exec_command(
            f"grep tuning  {self.args.sosreport_path}/etc/foreman-installer/scenarios.d/satellite.yaml | cut -d ':' -f2")  # noqa E501
        self.sos['satversion'] = self.util.exec_command(
            f"grep -E 'satellite-6' {self.args.sosreport_path}/installed-rpms | cut -d ' ' -f1").strip()  # noqa E501
        self.dynflowdata['version'] = self.util.exec_command(
            f"tail -n3 {self.args.sosreport_path}/sos_commands/foreman/dynflow_schema_info | head -1 | sed 's/ *//'").strip()  # noqa E501
        self.sos['sosname'] = os.path.basename(
            os.path.normpath(self.args.sosreport_path))
        if self.sos['sosname'] == ".":
            self.sos['sosname'] = ""
