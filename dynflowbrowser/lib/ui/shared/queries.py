"""Shared database queries and data fetching for UI implementations."""
import html
import json


class ActionQueries:
    """Common queries for fetching action and step data."""

    @staticmethod
    def get_actions_for_plan(db, plan_uuid):
        """Query all actions for a specific plan with full details.

        Args:
            db: OutputSQLite or InputPostgres database instance
            plan_uuid: The execution plan UUID

        Returns:
            list: Action records with aggregated step data
        """
        # Detect database type
        is_postgres = hasattr(db, '_conn') and hasattr(
            db._conn, 'server_version'
        )

        if is_postgres:
            # PostgreSQL: Query from actions table for one row per action
            # Use DISTINCT ON to guarantee uniqueness by action id
            sql = (
                "SELECT a.id, a.execution_plan_uuid, a.caller_action_id,"
                + " a.run_step_id, a.class, a.data, a.input, a.output,"
                + " (SELECT p.result FROM dynflow_execution_plans p"
                + "  WHERE p.uuid = a.execution_plan_uuid LIMIT 1),"
                + " (SELECT p.label FROM dynflow_execution_plans p"
                + "  WHERE p.uuid = a.execution_plan_uuid LIMIT 1),"
                + " (SELECT MIN(s.state) FROM dynflow_steps s"
                + "  WHERE s.execution_plan_uuid = a.execution_plan_uuid"
                + "  AND s.action_id = a.id),"
                + " a.caller_execution_plan_id,"
                + " (SELECT t.action FROM foreman_tasks_tasks t"
                + "  WHERE t.external_id::uuid = a.execution_plan_uuid LIMIT 1),"
                + " (SELECT t.id::text FROM foreman_tasks_tasks t"
                + "  WHERE t.external_id::uuid = a.execution_plan_uuid LIMIT 1),"
                + " (SELECT t.parent_task_id::text FROM foreman_tasks_tasks t"
                + "  WHERE t.external_id::uuid = a.execution_plan_uuid LIMIT 1),"
                + " (SELECT MIN(s.started_at) FROM dynflow_steps s"
                + "  WHERE s.execution_plan_uuid = a.execution_plan_uuid"
                + "  AND s.action_id = a.id),"
                + " (SELECT MAX(s.ended_at) FROM dynflow_steps s"
                + "  WHERE s.execution_plan_uuid = a.execution_plan_uuid"
                + "  AND s.action_id = a.id),"
                + " (SELECT SUM(s.real_time) FROM dynflow_steps s"
                + "  WHERE s.execution_plan_uuid = a.execution_plan_uuid"
                + "  AND s.action_id = a.id),"
                + " (SELECT SUM(s.execution_time) FROM dynflow_steps s"
                + "  WHERE s.execution_plan_uuid = a.execution_plan_uuid"
                + "  AND s.action_id = a.id)"
                + " FROM dynflow_actions a"
                + " WHERE a.execution_plan_uuid = %s"
                + " ORDER BY a.id"
            )
        else:
            # SQLite: no casting needed
            # Use a.class from actions table, not s.action_class from steps
            sql = (
                "SELECT s.action_id, p.uuid, a.caller_action_id,"
                + " a.run_step_id, a.class, a.data, a.input, a.output,"
                + " p.result, p.label, MIN(s.state),"
                + " a.caller_execution_plan_id, MAX(t.action), MAX(t.id),"
                + " MAX(t.parent_task_id),"
                + " MIN(s.started_at), MAX(s.ended_at),"
                + " SUM(s.real_time), SUM(s.execution_time)"
                + " FROM dynflow_steps s"
                + " LEFT JOIN foreman_tasks_tasks t"
                + " ON s.execution_plan_uuid = t.external_id"
                + " LEFT JOIN dynflow_execution_plans p"
                + " ON s.execution_plan_uuid = p.uuid"
                + " LEFT JOIN dynflow_actions a"
                + " ON s.execution_plan_uuid = a.execution_plan_uuid"
                + " AND s.action_id = a.id"
                + " WHERE s.execution_plan_uuid = ?"
                + " GROUP BY s.execution_plan_uuid, s.action_id"
            )

        return db.query(sql, (plan_uuid,))

    @staticmethod
    def get_actions_simple(db, plan_uuid):
        """Query actions for a plan without aggregation.

        Args:
            db: OutputSQLite or InputPostgres database instance
            plan_uuid: The execution plan UUID

        Returns:
            list: Action records
        """
        # Detect database type
        is_postgres = hasattr(db, '_conn') and hasattr(
            db._conn, 'server_version'
        )

        if is_postgres:
            sql = """
                SELECT a.id, a.execution_plan_uuid, a.caller_action_id,
                       a.run_step_id, a.class, a.data, a.input, a.output,
                       p.result, p.label,
                       a.caller_execution_plan_id
                FROM dynflow_actions a
                LEFT JOIN dynflow_execution_plans p
                    ON a.execution_plan_uuid = p.uuid
                WHERE a.execution_plan_uuid = %s
                ORDER BY a.id
            """
        else:
            sql = """
                SELECT a.id, a.execution_plan_uuid, a.caller_action_id,
                       a.run_step_id, a.class, a.data, a.input, a.output,
                       p.result, p.label,
                       a.caller_execution_plan_id
                FROM dynflow_actions a
                LEFT JOIN dynflow_execution_plans p
                    ON a.execution_plan_uuid = p.uuid
                WHERE a.execution_plan_uuid = ?
                ORDER BY a.id
            """
        return db.query(sql, (plan_uuid,))

    @staticmethod
    def get_steps_for_plan(db, plan_uuid):
        """Query all steps for a specific plan.

        Args:
            db: OutputSQLite or InputPostgres database instance
            plan_uuid: The execution plan UUID

        Returns:
            list: Step records
        """
        # Detect database type
        is_postgres = hasattr(db, '_conn') and hasattr(
            db._conn, 'server_version'
        )

        if is_postgres:
            sql = """
                SELECT * FROM dynflow_steps
                WHERE execution_plan_uuid = %s
                ORDER BY id
            """
        else:
            sql = """
                SELECT * FROM dynflow_steps
                WHERE execution_plan_uuid = ?
                ORDER BY id
            """
        return db.query(sql, (plan_uuid,))

    @staticmethod
    def get_steps_by_action(db, plan_uuid):
        """Query steps for a plan grouped by action_id.

        Args:
            db: OutputSQLite database instance
            plan_uuid: The execution plan UUID

        Returns:
            dict: Steps grouped by action_id
        """
        all_steps = ActionQueries.get_steps_for_plan(db, plan_uuid)

        steps_by_action = {}
        for step in all_steps:
            action_id = step[2]  # action_id is at index 2
            if action_id not in steps_by_action:
                steps_by_action[action_id] = []
            steps_by_action[action_id].append(step)

        return steps_by_action


class StatsQueries:
    """Common queries for execution statistics."""

    @staticmethod
    def get_dynflow_total_exectime(db, conf=None):
        """Get top Dynflow steps by total execution time.

        Filtering strategy:
        - SQLite: Use includedUUID (only those tasks were imported from CSV)
        - PostgreSQL: Use WHERE clause with user filters (live real-time data)

        Args:
            db: OutputSQLite or InputPostgres database instance
            conf: Optional Configuration object with filter data

        Returns:
            list: Query results with (sum_exec_time, count, action_class)
        """
        # Detect database type
        is_postgres = hasattr(db, '_conn') and hasattr(
            db._conn, 'server_version'
        )

        if is_postgres and conf:
            # PostgreSQL: Use WHERE clause with user filters for live data
            from dynflowbrowser import DynflowBrowser
            browser = DynflowBrowser()
            browser.conf = conf
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

            sql = f"""
                SELECT SUM(s.execution_time), COUNT(s.id), s.action_class
                FROM dynflow_steps s
                JOIN foreman_tasks_tasks t ON s.execution_plan_uuid = t.external_id::uuid
                WHERE {where_clause_prefixed}
                GROUP BY s.action_class
                ORDER BY SUM(s.execution_time) DESC
                LIMIT 5
            """
            return db.query(sql, params or ())
        elif conf and conf.dynflowdata.get('includedUUID'):
            # SQLite: Use includedUUID list (static snapshot)
            uuids = conf.dynflowdata['includedUUID']
            placeholders = ','.join('?' * len(uuids))
            sql = f"""
                SELECT SUM(execution_time), COUNT(s.id), s.action_class
                FROM dynflow_steps s
                WHERE s.execution_plan_uuid IN ({placeholders})
                GROUP BY s.action_class
                ORDER BY SUM(execution_time) DESC
                LIMIT 5
            """
            return db.query(sql, tuple(uuids))
        else:
            # No filtering - all steps
            sql = """
                SELECT SUM(execution_time), COUNT(s.id), s.action_class
                FROM dynflow_steps s
                GROUP BY s.action_class
                ORDER BY SUM(execution_time) DESC
                LIMIT 5
            """
            return db.query(sql)

    @staticmethod
    def get_dynflow_plan_exectime(db, plan_uuid):
        """Get Dynflow execution times for a specific plan.

        Args:
            db: OutputSQLite or InputPostgres database instance
            plan_uuid: The execution plan UUID

        Returns:
            list: Top execution times for this plan
        """
        # Detect database type
        is_postgres = hasattr(db, '_conn') and hasattr(
            db._conn, 'server_version'
        )

        if is_postgres:
            sql = """
                SELECT SUM(execution_time), COUNT(s.id), s.action_class
                FROM dynflow_steps s
                WHERE s.execution_plan_uuid = %s
                GROUP BY s.action_class
                ORDER BY SUM(execution_time) DESC
                LIMIT 5
            """
        else:
            sql = """
                SELECT SUM(execution_time), COUNT(s.id), s.action_class
                FROM dynflow_steps s
                WHERE s.execution_plan_uuid = ?
                GROUP BY s.action_class
                ORDER BY SUM(execution_time) DESC
                LIMIT 5
            """
        return db.query(sql, (plan_uuid,))

    @staticmethod
    def get_all_actions_with_pulp(db):
        """Get all actions that have pulp_tasks in output.

        Args:
            db: OutputSQLite database instance

        Returns:
            list: Actions with output field
        """
        sql = "SELECT a.output FROM dynflow_actions a"
        return db.query(sql)

    @staticmethod
    def get_actions_with_pulp_for_plan(db, plan_uuid):
        """Get actions with pulp_tasks for a specific plan.

        Args:
            db: OutputSQLite or InputPostgres database instance
            plan_uuid: The execution plan UUID

        Returns:
            list: Actions with output field
        """
        # Detect database type
        is_postgres = hasattr(db, '_conn') and hasattr(
            db._conn, 'server_version'
        )

        if is_postgres:
            sql = """
                SELECT a.output
                FROM dynflow_actions a
                WHERE a.execution_plan_uuid = %s
            """
        else:
            sql = """
                SELECT a.output
                FROM dynflow_actions a
                WHERE a.execution_plan_uuid = ?
            """
        return db.query(sql, (plan_uuid,))


class FormatHelpers:
    """Helper functions for formatting data."""

    @staticmethod
    def show_json(txt):
        """Format JSON text with indentation and HTML escaping.

        Args:
            txt: JSON text to format

        Returns:
            str: Formatted JSON or original text
        """
        if not txt:
            return txt

        try:
            # Try to parse and format as JSON
            parsed = json.loads(txt)
            formatted = json.dumps(parsed, indent=4)
            return html.escape(formatted)
        except Exception:
            # Not JSON or parsing failed, return as-is
            return txt

    @staticmethod
    def format_steps_with_json(rows, show_all=True):
        """Format step rows by parsing JSON fields.

        Args:
            rows: List of step tuples from database
            show_all: If False, filter out success steps

        Returns:
            dict: Steps grouped by (execution_plan_uuid, action_id)
        """
        steps = {}

        for r in rows:
            if not show_all and r[8] == "success":
                continue

            r = list(r)
            # Format JSON fields (indices from steps table schema)
            r[12] = FormatHelpers.show_json(r[12])  # queue
            r[13] = FormatHelpers.show_json(r[13])  # error
            r[14] = FormatHelpers.show_json(r[14])  # children
            r[15] = FormatHelpers.show_json(r[15])  # data

            execution_plan_uuid = r[0]
            action_id = r[2]

            if execution_plan_uuid not in steps:
                steps[execution_plan_uuid] = {}

            if action_id not in steps[execution_plan_uuid]:
                steps[execution_plan_uuid][action_id] = []

            steps[execution_plan_uuid][action_id].append(r)

        return steps

    @staticmethod
    def parse_pulp_tasks(output_json):
        """Parse pulp_tasks from action output JSON.

        Args:
            output_json: JSON string containing pulp_tasks

        Returns:
            list: Pulp task dictionaries, or empty list if none found
        """
        if not output_json:
            return []

        try:
            data = json.loads(output_json)
            if 'pulp_tasks' in data:
                return data['pulp_tasks']
        except Exception:
            pass

        return []
