"""PostgreSQL input module for direct database access."""
from datetime import datetime
import json

import msgpack
import psycopg2


class InputPostgres:
    """Read-only PostgreSQL connection for direct database access.

    Provides the same query interface as OutputSQLite for compatibility.
    """

    def __init__(self, conf, error_callback=None):
        """Initialize PostgreSQL connection.

        Args:
            conf: Configuration object with db_params
            error_callback: Optional callback for error messages
        """
        self.conf = conf
        self.error_callback = error_callback
        self._conn = None
        self._cursor = None

        # Parse server:port
        server_parts = conf.db_params['server'].split(':')
        self.host = server_parts[0]
        self.port = int(server_parts[1]) if len(server_parts) > 1 else 5432

        self.database = conf.db_params['database']
        self.user = conf.db_params['username']
        self.password = conf.db_params['password']

        self.connect()

    def connect(self):
        """Establish PostgreSQL connection (read-only)."""
        try:
            self._conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )

            # Set read-only mode for safety
            self._conn.set_session(readonly=True, autocommit=True)
            # Explicitly create cursor (inherits DictCursor from connection)
            self._cursor = self._conn.cursor()

            # Fetch and update timezone from PostgreSQL server
            self._fetch_server_timezone()

            # Fetch and update Dynflow schema version
            self._fetch_schema_version()

        except psycopg2.OperationalError as e:
            error_msg = f"Failed to connect to PostgreSQL: {e}"
            if self.error_callback:
                self.error_callback(error_msg)
            else:
                print(f"ERROR: {error_msg}")
            raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _fetch_server_timezone(self):
        """Fetch timezone from PostgreSQL server and update conf."""
        try:
            self._cursor.execute("SHOW timezone")
            result = self._cursor.fetchone()
            if result:
                timezone = result[0]
                # Update conf with server timezone
                self.conf.sos['timezone'] = timezone
        except Exception:
            # If we can't get timezone, keep the default UTC
            pass

    def _fetch_schema_version(self):
        """Fetch Dynflow schema version from PostgreSQL and update conf."""
        try:
            # Query the version from dynflow_schema_info table
            # The table has a single row with a 'version' column
            self._cursor.execute("SELECT version FROM dynflow_schema_info")
            result = self._cursor.fetchone()
            if result:
                # Get the version number (integer)
                version = result[0]
                # Store as string (matching sosreport format)
                self.conf.dynflowdata['version'] = str(version).strip()
        except Exception:
            # If we can't get version, keep the default Unknown
            pass  # noqa: S110

    @property
    def connection(self):
        return self._conn

    @property
    def cursor(self):
        return self._cursor

    def close(self, commit=True):  # noqa: ARG002
        """Close PostgreSQL connection.

        Args:
            commit: Ignored for read-only connections
                    (compatibility with OutputSQLite)
        """
        if self._cursor:
            self._cursor.close()
        if self._conn:
            self._conn.close()

    def execute(self, sql, params=None):
        """Execute SQL statement.

        Args:
            sql: SQL query string (SQLite format with ? or PostgreSQL with %s)
            params: Query parameters tuple
        """
        # Handle both SQLite-style (?) and PostgreSQL-style (%s) placeholders
        if '?' in sql:
            # SQLite format: convert ? to %s
            # Simply replace ? with %s - don't escape % in string literals
            # psycopg2 handles % correctly inside quoted strings
            sql_postgres = sql.replace('?', '%s')
        elif '%s' in sql:
            # Already PostgreSQL format with %s placeholders - use as-is
            sql_postgres = sql
        else:
            # No placeholders, but may have literal % in LIKE clauses
            # Escape all % to %%
            sql_postgres = sql.replace('%', '%%')

        self.cursor.execute(sql_postgres, params or ())

    def fetchall(self):
        """Fetch all rows from last query.

        Converts bytea/memoryview columns to strings for compatibility.
        """
        rows = self.cursor.fetchall()
        return [self._decode_row(row) for row in rows]

    def fetchone(self):
        """Fetch one row from last query.

        Converts bytea/memoryview columns to strings for compatibility.
        """
        row = self.cursor.fetchone()
        return self._decode_row(row) if row else None

    def _decode_row(self, row):
        """Decode bytea/memoryview columns to strings.

        PostgreSQL bytea columns contain MessagePack-encoded data.

        Args:
            row: tuple from psycopg2

        Returns:
            tuple: Row with bytea columns decoded to JSON strings
        """
        if not row:
            return row

        decoded = []
        for value in row:
            # Convert datetime to ISO format strings (SQLite compatibility)
            if isinstance(value, datetime):
                decoded.append(value.isoformat())
            # Convert memoryview/bytes to string
            elif isinstance(value, (memoryview, bytes)):
                try:
                    # Dynflow data is MessagePack encoded
                    data_bytes = bytes(value)
                    # Decode MessagePack to Python object
                    unpacked = msgpack.unpackb(data_bytes, raw=False)
                    # Convert ExtType objects to a serializable format
                    unpacked = self._convert_msgpack_ext(unpacked)
                    # Convert to JSON string (matching SQLite TEXT format)
                    decoded.append(json.dumps(unpacked))
                except (msgpack.exceptions.ExtraData,
                        msgpack.exceptions.UnpackException,
                        UnicodeDecodeError,
                        TypeError):
                    # If MessagePack decode fails, try plain UTF-8
                    try:
                        decoded.append(data_bytes.decode('utf-8'))
                    except UnicodeDecodeError:
                        # Last resort: string representation
                        decoded.append(str(value))
            else:
                decoded.append(value)

        # Return tuple to match SQLite's return type
        return tuple(decoded)

    def _convert_msgpack_ext(self, obj):
        """Convert MessagePack ExtType objects to JSON-serializable format.

        Args:
            obj: Object potentially containing ExtType instances

        Returns:
            Object with ExtType instances converted to strings
        """
        if isinstance(obj, dict):
            return {k: self._convert_msgpack_ext(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_msgpack_ext(item) for item in obj]
        elif isinstance(obj, msgpack.ExtType):
            # Convert ExtType to base64 string representation
            import base64
            return f"ExtType(code={obj.code}, data={base64.b64encode(obj.data).decode('ascii')})"
        else:
            return obj

    def query(self, sql, params=None):
        """Execute query and return all results.

        Args:
            sql: SQL query string (SQLite format with ?)
            params: Query parameters tuple

        Returns:
            list: Query results
        """
        self.execute(sql, params)
        return self.fetchall()

    def read_tasks(self, where_clause="TRUE", params=None):
        """Read tasks with optional WHERE clause.

        Args:
            where_clause: SQL WHERE condition
            params: Query parameters tuple

        Returns:
            list: Task rows
        """
        sql = f"""
            SELECT id, type, label, started_at, ended_at,
                   state, result, external_id, parent_task_id,
                   start_at, start_before, action, state_updated_at, user_id
            FROM foreman_tasks_tasks
            WHERE {where_clause}
            ORDER BY started_at DESC
        """
        return self.query(sql, params)

    def read_plans(self, where_clause="TRUE", params=None):
        """Read execution plans with optional WHERE clause.

        Args:
            where_clause: SQL WHERE condition
            params: Query parameters tuple

        Returns:
            list: Plan rows
        """
        sql = f"""
            SELECT uuid, state, result, started_at, ended_at,
                   real_time, execution_time, label, class,
                   root_plan_step_id, run_flow, finalize_flow,
                   execution_history, step_ids, data
            FROM dynflow_execution_plans
            WHERE {where_clause}
        """
        return self.query(sql, params)

    def read_actions(self, where_clause="TRUE", params=None):
        """Read actions with optional WHERE clause.

        Args:
            where_clause: SQL WHERE condition
            params: Query parameters tuple

        Returns:
            list: Action rows
        """
        sql = f"""
            SELECT execution_plan_uuid, id, caller_execution_plan_id,
                   caller_action_id, class, plan_step_id,
                   run_step_id, finalize_step_id, data, input, output
            FROM dynflow_actions
            WHERE {where_clause}
        """
        return self.query(sql, params)

    def read_steps(self, where_clause="TRUE", params=None):
        """Read steps with optional WHERE clause.

        Args:
            where_clause: SQL WHERE condition
            params: Query parameters tuple

        Returns:
            list: Step rows
        """
        sql = f"""
            SELECT execution_plan_uuid, id, action_id, state,
                   started_at, ended_at, real_time, execution_time,
                   progress_done, progress_weight, class, action_class,
                   queue, error, children, data
            FROM dynflow_steps
            WHERE {where_clause}
        """
        return self.query(sql, params)

    # Compatibility methods - not used for PostgreSQL
    def create_tables(self):
        """Not needed for PostgreSQL - tables already exist."""
        return  # Compatibility method - no-op for PostgreSQL

    def create_indexes(self):
        """Not needed for PostgreSQL - indexes already exist."""
        return  # Compatibility method - no-op for PostgreSQL

    def commit(self):
        """Not needed for read-only connections."""
        return  # Compatibility method - no-op for read-only
