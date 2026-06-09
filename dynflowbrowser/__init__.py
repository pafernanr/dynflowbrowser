import datetime

from dynflowbrowser.lib.configuration import Conf
from dynflowbrowser.lib.inputdynflow import InputDynflow
from dynflowbrowser.lib.outputsqlite import OutputSQLite
from dynflowbrowser.lib.search_parser import SearchParser
from dynflowbrowser.lib.util import Util


class DynflowBrowser:

    def __init__(self):
        # Initialize in TUI mode to skip console prompts
        self.conf = Conf(tui_mode=True)
        self.util = Util()

        # Only create InputDynflow for SQLite mode (reads CSV files)
        # For PostgreSQL mode, we don't need it
        if not self.conf.args.dbserver:
            self.input_dynflow = InputDynflow(self.conf)
        else:
            self.input_dynflow = None
            # Initialize schema structure for PostgreSQL mode
            # This will be updated with actual version from database later
            self._init_dynflow_schema_defaults()

        self.search_parser = SearchParser()

    def _init_dynflow_schema_defaults(self):
        """Initialize dynflowdata schema structure for PostgreSQL mode.

        The version will be updated when InputPostgres connects.
        Using schema version 24/25 structure as default.
        """
        self.conf.dynflowdata['tasks'] = {
            'inputfile': '',  # Not used for PostgreSQL
            'sortby': 'started_at',
            'reverse': True,
            'dates': ['started_at', 'ended_at', 'state_updated_at'],
            'json': [],
            'headers': ['id', 'type', 'label', 'started_at', 'ended_at',
                        'state', 'result', 'external_id', 'parent_task_id',
                        'start_at', 'start_before', 'action', 'user_id',
                        'state_updated_at']
        }

        self.conf.dynflowdata['plans'] = {
            'inputfile': '',
            'sortby': 'started_at',
            'reverse': True,
            'dates': ['started_at', 'ended_at'],
            'json': ['run_flow', 'execution_history', 'step_ids', 'data'],
            'headers': ['uuid', 'state', 'result', 'started_at', 'ended_at',
                        'real_time', 'execution_time', 'label', 'class',
                        'root_plan_step_id', 'run_flow', 'finalize_flow',
                        'execution_history', 'step_ids', 'data']
        }

        self.conf.dynflowdata['actions'] = {
            'inputfile': '',
            'sortby': 'id',
            'reverse': False,
            'dates': [],
            'json': ['data', 'input', 'output'],
            'headers': ['execution_plan_uuid', 'id',
                        'caller_execution_plan_id', 'caller_action_id',
                        'class', 'plan_step_id', 'run_step_id',
                        'finalize_step_id', 'data', 'input', 'output']
        }

        self.conf.dynflowdata['steps'] = {
            'inputfile': '',
            'sortby': 'id',
            'reverse': False,
            'dates': ['started_at', 'ended_at'],
            'json': ['queue', 'error', 'children', 'data'],
            'headers': ['execution_plan_uuid', 'id', 'action_id', 'state',
                        'started_at', 'ended_at', 'real_time',
                        'execution_time', 'progress_done', 'progress_weight',
                        'class', 'action_class', 'queue', 'error',
                        'children', 'data']
        }

    def build_filters_sql(self):
        """Build SQL WHERE clause and parameters for PostgreSQL filtering.

        Returns:
            tuple: (where_clause, params) for SQL query
        """
        clauses = []
        params = []

        # Task days filter
        if self.conf.args.task_days:
            # PostgreSQL INTERVAL needs the value concatenated, not as a parameter
            clauses.append(
                f"(started_at > NOW() - INTERVAL '{self.conf.args.task_days} days' OR "
                f"ended_at > NOW() - INTERVAL '{self.conf.args.task_days} days')"
            )

        # State filter
        if self.conf.args.state:
            clauses.append("LOWER(state) = %s")
            params.append(self.conf.args.state.lower())

        # Result filter
        if self.conf.args.result:
            clauses.append("LOWER(result) = %s")
            params.append(self.conf.args.result.lower())

        # Search filter - translate to SQL
        if self.conf.args.search:
            search_sql, search_params = self.translate_search_to_sql(
                self.conf.args.search
            )
            clauses.append(search_sql)
            params.extend(search_params)

        # Combine with AND
        where_sql = " AND ".join(clauses) if clauses else "TRUE"
        return where_sql, params

    def translate_search_to_sql(self, search_query):
        """Convert SearchParser syntax to PostgreSQL WHERE clause.

        Args:
            search_query: Search query string

        Returns:
            tuple: (sql_clause, params) for SQL query
        """
        conditions = self.search_parser.parse(search_query)

        sql_parts = []
        params = []

        for field, operator, value, connector in conditions:
            # Map operators to SQL
            if operator == '=':
                sql_parts.append(f"LOWER({field}) = %s")
                params.append(value.lower())
            elif operator == '!=':
                sql_parts.append(f"LOWER({field}) != %s")
                params.append(value.lower())
            elif operator == '~':  # contains
                sql_parts.append(f"{field} ILIKE %s")
                params.append(f"%{value}%")
            elif operator == '!~':  # not contains
                sql_parts.append(f"{field} NOT ILIKE %s")
                params.append(f"%{value}%")
            elif operator in ['>', '<', '>=', '<=']:
                sql_parts.append(f"{field} {operator} %s")
                params.append(value)

            # Add connector
            if connector:
                sql_parts.append(connector)

        return "(" + " ".join(sql_parts) + ")", params

    def main(self):
        headers = self.conf.dynflowdata['tasks']['headers']

        if self.conf.args.dbserver:
            # PostgreSQL mode
            # In TUI mode, skip connection here - will be handled by TUI modal
            # In console mode, we already prompted for credentials
            if not self.conf.tui_mode:
                # Console mode - connect now
                from dynflowbrowser.lib.inputpostgres import InputPostgres

                try:
                    db = InputPostgres(self.conf)
                except Exception as e:
                    print("\nERROR: Failed to connect to PostgreSQL")
                    print(f"Details: {e}")
                    print(
                        "\nPlease check your connection parameters "
                        "and try again."
                    )
                    import sys
                    sys.exit(1)

                # Build WHERE clause for efficient filtering
                where_clause, params = self.build_filters_sql()

                # Read only filtered tasks from PostgreSQL
                dynflow = db.read_tasks(where_clause, params)

                # Convert DictRow to list for compatibility
                dynflow = [list(row) for row in dynflow]

                # Store ALL UUIDs from filtered results
                for row in dynflow:
                    external_id = row[headers.index('external_id')]
                    self.conf.dynflowdata['includedUUID'].append(external_id)
            else:
                # TUI mode - db will be set by TUI after connection modal
                db = None

        else:
            # SQLite mode - read CSV and filter in Python
            sqlite = OutputSQLite(self.conf)
            dynflow = self.input_dynflow.read_dynflow('tasks')

            # Calculate date range if --task-days is specified
            if self.conf.args.task_days:
                dto = self.util.date_from_string(self.conf.sos['localtime'])
                dfrom = dto - datetime.timedelta(days=self.conf.args.task_days)
            else:
                # Default: all time
                dfrom = self.util.date_from_string('1974-04-10')
                dto = self.util.date_from_string('2999-01-01')
            # workaround for disordered fields on some csv files
            # user_id is an integer en psql hence len=10
            if len(dynflow[2][13]) < 11:
                self.conf.dynflowdata['tasks']['headers'] = [
                    'id', 'dtype', 'label', 'started_at', 'ended_at',
                    'state', 'result', 'external_id', 'parent_task_id',
                    'start_at', 'start_before', 'action',
                    'state_updated_at', 'user_id']
            # end workaround
            for i, dline in enumerate(dynflow):
                # exclude task if not between arguments dfrom and dto
                starts = "1974-04-10"
                ends = "2999-01-01"
                if 'started_at' in headers:
                    istarts = headers.index('started_at')
                    iends = headers.index('ended_at')
                    if dline[istarts] != "":
                        starts = dline[istarts]
                    if dline[iends] != "":
                        ends = dline[iends]
                starts = self.util.change_timezone(
                    self.conf.sos['timezone'],
                    starts)
                ends = self.util.change_timezone(
                    self.conf.sos['timezone'],
                    ends)
                # Filter by date range
                if (dfrom <= starts <= dto) or (dfrom <= ends <= dto):
                    include_task = True

                    # Filter by state if --state is specified
                    if self.conf.args.state:
                        task_state = dline[headers.index('state')].lower()
                        if task_state != self.conf.args.state.lower():
                            include_task = False

                    # Filter by result if --result is specified
                    if include_task and self.conf.args.result:
                        task_result = dline[headers.index('result')].lower()
                        if task_result != self.conf.args.result.lower():
                            include_task = False

                    # Filter by search query if --search is specified
                    if include_task and self.conf.args.search:
                        conditions = self.search_parser.parse(
                            self.conf.args.search
                        )
                        if not self.search_parser.evaluate(
                                conditions, dline, headers):
                            include_task = False

                    if include_task:
                        self.conf.dynflowdata['includedUUID'].append(
                            dline[headers.index('external_id')]
                        )

        # Route to UI - pass database connection to UI layer
        from dynflowbrowser.lib.ui.text.output import TextOutput
        output = TextOutput(self.conf)

        if self.conf.args.dbserver:
            # PostgreSQL mode
            # Pass postgres=db (might be None for TUI mode)
            # TUI will show connection modal if db is None
            output.write(
                postgres=db,
                input_dynflow=None
            )
        else:
            # SQLite mode
            output.write(
                sqlite=sqlite,
                input_dynflow=self.input_dynflow
            )  # Blocking call - runs until user quits
