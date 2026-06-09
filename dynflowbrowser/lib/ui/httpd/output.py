"""HTTP dynamic output implementation."""
import json
import os
import shutil
import time

from dynflowbrowser.lib.outputsqlite import OutputSQLite
from dynflowbrowser.lib.ui.base import BaseOutput
from dynflowbrowser.lib.ui.base import BaseDataProvider
from dynflowbrowser.lib.ui.httpd.server import DynamicHttpServer
from dynflowbrowser.lib.util import Util


class HttpdOutput(BaseOutput):
    """HTTP dynamic output - serves content via HTTP server."""

    def __init__(self, conf, postgres=None):
        """Initialize HTTP dynamic output.

        Args:
            conf: Configuration object with args and settings
            postgres: Optional InputPostgres instance (PostgreSQL mode)
        """
        super().__init__(conf)
        # Use PostgreSQL if provided, otherwise create SQLite
        if postgres:
            self.db = postgres
        else:
            self.db = OutputSQLite(conf)
        self.util = Util()
        self.data_provider = BaseDataProvider(self.db, conf)

    def write(self):
        """Start HTTP server and serve dynamic content.

        This is the main entry point called from the main loop.
        """
        import time

        # Compute execution time statistics (needed for display)
        t_start = time.time()
        self.compute_execution_stats()
        t_stats = time.time()
        print(f"[DEBUG] compute_execution_stats took: {t_stats - t_start:.2f}s")

        # Copy static assets to output directory
        self.copy_static_assets()
        t_assets = time.time()
        print(f"[DEBUG] copy_static_assets took: {t_assets - t_stats:.2f}s")

        # Get dynflow total execution time stats
        dynflow_stats = self.data_provider.get_dynflow_total_exectime()
        t_dynflow = time.time()
        print(f"[DEBUG] get_dynflow_total_exectime took: {t_dynflow - t_assets:.2f}s")

        # Start HTTP server with pre-computed statistics
        # Reuse PostgreSQL connection if available
        server = DynamicHttpServer(
            self.conf,
            self.data_provider.pulp_total_exectime,
            dynflow_stats,
            quiet=False,
            data_provider=self.data_provider,
            postgres_connection=self.db if self.conf.args.dbserver else None
        )
        server.start()

        try:
            # Keep server running until Ctrl+C
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down HTTP server...")
            try:
                server.stop()
            except KeyboardInterrupt:
                # Suppress second Ctrl+C during shutdown
                pass

    def write_tasks(self):
        """Not used in HTTP mode - tasks are generated on-demand."""
        return

    def write_actions(self):
        """Not used in HTTP mode - only tasks view is dynamic."""
        return

    def copy_static_assets(self):
        """Copy static CSS/JS files to output directory."""
        static_src = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "static"
        )
        static_dest = self.conf.args.output_path + "/html"

        if os.path.exists(static_dest):
            shutil.rmtree(static_dest)

        if os.path.exists(static_src):
            shutil.copytree(static_src, static_dest)

    def compute_execution_stats(self):
        """Compute Pulp and Dynflow execution statistics.

        Filtering strategy:
        - SQLite: Use includedUUID (only those tasks were imported)
        - PostgreSQL: Use WHERE clause with user filters (live data)

        Returns:
            tuple: (pulp_stats, dynflow_stats)
        """
        # Detect database type
        is_postgres = self.conf.args.dbserver

        # Enable query-only mode for better performance (SQLite only)
        if not is_postgres:
            self.db.execute("PRAGMA query_only = ON")

        if is_postgres:
            # PostgreSQL: Build WHERE clause from user filters
            from dynflowbrowser import DynflowBrowser
            browser = DynflowBrowser()
            browser.conf = self.conf
            where_clause, params = browser.build_filters_sql()

            # Prefix column names with 't.' for foreman_tasks_tasks table
            where_clause_prefixed = where_clause.replace(
                'started_at', 't.started_at'
            ).replace(
                'ended_at', 't.ended_at'
            ).replace(
                'state', 't.state'
            ).replace(
                'result', 't.result'
            ).replace(
                'label', 't.label'
            ).replace(
                'action', 't.action'
            )

            # Query actions with pulp_tasks using filters
            sql = f"""
                SELECT a.execution_plan_uuid, a.output
                FROM dynflow_actions a
                JOIN foreman_tasks_tasks t ON a.execution_plan_uuid = t.external_id::uuid
                WHERE {where_clause_prefixed}
                AND a.output LIKE '%pulp_tasks%'
            """
            rows = self.db.query(sql, params or ())

            # Query steps using filters
            sql_steps = f"""
                SELECT s.execution_plan_uuid, s.action_class, s.execution_time
                FROM dynflow_steps s
                JOIN foreman_tasks_tasks t ON s.execution_plan_uuid = t.external_id::uuid
                WHERE {where_clause_prefixed}
            """
            steps = self.db.query(sql_steps, params or ())

        elif self.conf.dynflowdata['includedUUID']:
            # SQLite: Use includedUUID list (static snapshot)
            uuid_placeholders = ','.join(
                '?' * len(self.conf.dynflowdata['includedUUID'])
            )
            sql = (
                "SELECT execution_plan_uuid, output "
                + "FROM dynflow_actions "
                + f"WHERE execution_plan_uuid IN ({uuid_placeholders}) "
                + "AND output LIKE '%pulp_tasks%'"
            )
            rows = self.db.query(
                sql,
                tuple(self.conf.dynflowdata['includedUUID'])
            )

            sql_steps = (
                "SELECT execution_plan_uuid, action_class, execution_time "
                + "FROM dynflow_steps "
                + f"WHERE execution_plan_uuid IN ({uuid_placeholders})"
            )
            steps = self.db.query(
                sql_steps,
                tuple(self.conf.dynflowdata['includedUUID'])
            )
        else:
            # No filtering
            rows = []
            steps = []

        # Process pulp tasks from actions output
        for row in rows:
            plan_uuid, output = row
            self.sum_pulp_plans_exectime(plan_uuid, output)

        # Aggregate dynflow execution times
        for step in steps:
            plan_uuid, action_class, exec_time = step
            self.sum_dynflow_plans_exectime(
                plan_uuid,
                action_class,
                exec_time
            )

        # Disable query-only mode (SQLite only)
        if not is_postgres:
            self.db.execute("PRAGMA query_only = OFF")

        # Return the computed statistics
        return (
            self.data_provider.pulp_total_exectime,
            self.data_provider.get_dynflow_total_exectime()
        )

    def sum_pulp_plans_exectime(self, puid, txt):
        """Parse and aggregate Pulp task times for a specific plan.

        Args:
            puid: Plan UUID
            txt: JSON text containing pulp_tasks data
        """
        if puid not in self.data_provider.pulp_plans_exectime:
            self.data_provider.pulp_plans_exectime[puid] = {}

        try:
            j = json.loads(txt)
            for task in j["pulp_tasks"]:
                finished_at = self.util.date_from_string(
                    task['finished_at']
                )
                pulp_created = self.util.date_from_string(
                    task['pulp_created']
                )
                pulp_exectime = (
                    (finished_at - pulp_created).total_seconds()
                )

                self.sum_pulp_total_exectime(
                    task['name'],
                    pulp_created,
                    finished_at,
                    pulp_exectime
                )

                try:
                    self.data_provider.pulp_plans_exectime[puid][
                        task['name']
                    ][0] += pulp_exectime
                    self.data_provider.pulp_plans_exectime[puid][
                        task['name']
                    ][1] += 1
                except Exception:
                    self.data_provider.pulp_plans_exectime[puid][
                        task['name']
                    ] = [pulp_exectime, 1]
        except Exception:
            pass

    def sum_pulp_total_exectime(
        self,
        name,
        started_at,
        finished_at,
        exectime
    ):
        """Aggregate Pulp task execution times across all plans.

        Args:
            name: Pulp task name
            started_at: Task start datetime
            finished_at: Task finish datetime
            exectime: Execution time in seconds
        """
        try:
            self.data_provider.pulp_total_exectime[name][0] += exectime
            self.data_provider.pulp_total_exectime[name][1] += 1
            self.data_provider.pulp_total_exectime[name][2] = finished_at
        except Exception:
            self.data_provider.pulp_total_exectime[name] = [
                exectime,
                1,
                started_at,
                finished_at
            ]

    def sum_dynflow_plans_exectime(self, puid, action_class, exectime):
        """Aggregate Dynflow action execution times per plan.

        Args:
            puid: Plan UUID
            action_class: Action class name
            exectime: Execution time in seconds
        """
        if puid not in self.data_provider.dynflow_plans_exectime:
            self.data_provider.dynflow_plans_exectime[puid] = {}

        try:
            self.data_provider.dynflow_plans_exectime[puid][
                action_class
            ][0] += exectime
            self.data_provider.dynflow_plans_exectime[puid][
                action_class
            ][1] += 1
        except Exception:
            self.data_provider.dynflow_plans_exectime[puid][
                action_class
            ] = [exectime, 1]
