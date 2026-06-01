"""HTTP server for dynamic content generation."""
import http.server
import os
import re
import socket
import socketserver
import subprocess
import threading

from jinja2 import Environment
from jinja2 import FileSystemLoader

from dynflowbrowser.lib.outputsqlite import OutputSQLite
from dynflowbrowser.lib.ui.base import BaseDataProvider
from dynflowbrowser.lib.ui.shared import ActionHierarchy
from dynflowbrowser.lib.ui.shared import ActionQueries
from dynflowbrowser.lib.ui.shared import FormatHelpers

class HttpServer:
    """HTTP server to serve generated HTML pages."""

    def __init__(self, output_path, quiet=False):
        """Initialize HTTP server.

        Args:
            output_path: Path to the directory containing generated HTML files
            quiet: If True, suppress output messages
        """
        self.output_path = output_path
        self.quiet = quiet
        self.server = None
        self.port = None
        self.ip_addresses = []

    def get_interface_for_ip(self, ip):
        """Get network interface name for a given IP address.

        Args:
            ip: IP address string

        Returns:
            str: Interface name or None if not found
        """
        try:
            # Try using 'ip addr' command (modern Linux)
            result = subprocess.run(['ip', 'addr'], capture_output=True,
                                    text=True, timeout=2)
            if result.returncode == 0:
                current_iface = None
                for line in result.stdout.split('\n'):
                    # Match interface name (e.g., "2: eth0:")
                    iface_match = re.match(r'^\d+:\s+(\S+):', line)
                    if iface_match:
                        current_iface = iface_match.group(1)
                    # Match IP address
                    if current_iface and f'inet {ip}/' in line:
                        return current_iface
        except Exception:
            pass

        # Fallback: try ifconfig
        try:
            result = subprocess.run(['ifconfig'], capture_output=True,
                                    text=True, timeout=2)
            if result.returncode == 0:
                current_iface = None
                for line in result.stdout.split('\n'):
                    # Match interface name (e.g., "eth0: flags=...")
                    iface_match = re.match(r'^(\S+):', line)
                    if iface_match:
                        current_iface = iface_match.group(1)
                    # Match IP address
                    if current_iface and f'inet {ip} ' in line:
                        return current_iface
        except Exception:
            pass

        return None

    def get_all_ips(self):
        """Get all available IP addresses for network interfaces.

        Returns:
            list: List of tuples (interface_name, ip_address)
        """
        ip_interfaces = []
        seen_ips = set()

        # Get hostname and resolve all IPs
        hostname = socket.gethostname()
        try:
            # Get all addresses associated with hostname
            addr_info = socket.getaddrinfo(hostname, None)
            for info in addr_info:
                ip = info[4][0]
                # Only include IPv4 addresses, exclude localhost
                if ':' not in ip and ip != '127.0.0.1' and ip not in seen_ips:
                    seen_ips.add(ip)
                    iface = self.get_interface_for_ip(ip)
                    ip_interfaces.append((iface, ip))
        except Exception:
            pass

        # If we didn't get any IPs, try the socket method
        if not ip_interfaces:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                if ip != '127.0.0.1':
                    iface = self.get_interface_for_ip(ip)
                    ip_interfaces.append((iface, ip))
            except Exception:
                pass

        # Fallback to localhost if nothing else works
        if not ip_interfaces:
            ip_interfaces.append((None, "127.0.0.1"))

        return ip_interfaces

    def get_fqdn(self):
        """Get the fully qualified domain name of the host.

        Returns:
            str: FQDN of the host
        """
        try:
            return socket.getfqdn()
        except Exception:
            return socket.gethostname()

    def get_direct_access_lines(self, url_path="/"):
        """Get direct HTTP access information lines.

        Args:
            url_path: Path to append to URLs (default: "/")

        Returns:
            list: List of strings with direct access information
        """
        lines = []
        for iface, ip in self.ip_addresses:
            url = f"http://{ip}:{self.port}{url_path}"
            if iface:
                lines.append(f"  {iface}: {url}")
            else:
                lines.append(f"  {url}")
        return lines

    def get_ssh_tunnel_lines(self, url_path="/"):
        """Get SSH tunnel access information lines.

        Args:
            url_path: Path to append to browser URL (default: "/")

        Returns:
            list: List of strings with SSH tunnel commands
        """
        hostname = self.get_fqdn()
        lines = ["1. Create SSH tunnel using the proper IP:"]

        # Add SSH commands for each available IP (except localhost)
        for iface, ip in self.ip_addresses:
            if ip != "127.0.0.1":
                lines.append(f"     ssh -L {self.port}:localhost:{self.port} {ip}")

        # Add hostname option as last option
        lines.append(f"     ssh -L {self.port}:localhost:{self.port} {hostname}")

        # Add the browser URL
        lines.extend([
            "",
            "2. Then open in browser:",
            f"     http://localhost:{self.port}{url_path}"
        ])

        return lines

    def find_free_port(self):
        """Find a free port in the user range (1024-65535).

        Returns:
            int: Available port number
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Bind to port 0 to let the OS assign a free port
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port

    def get_request_handler(self):
        """Get the HTTP request handler class.

        Subclasses can override this to provide custom handlers.

        Returns:
            class: HTTP request handler class
        """
        return http.server.SimpleHTTPRequestHandler

    def get_server_name(self):
        """Get the server name for display.

        Subclasses can override this.

        Returns:
            str: Server name
        """
        return "HTTP Server"

    def get_index_path(self):
        """Get the index path for URLs.

        Subclasses can override this.

        Returns:
            str: Index path (e.g., '/index.html' or '/')
        """
        return "/index.html"

    def start(self):
        """Start the HTTP server in a background thread.

        Returns:
            str: Primary URL to access the server
        """
        # Get free port
        self.port = self.find_free_port()

        # Change to output directory
        os.chdir(self.output_path)

        # Create HTTP server with ThreadingMixIn for concurrent requests
        class ThreadedHTTPServer(socketserver.ThreadingMixIn,
                                 http.server.HTTPServer):
            pass

        # Get request handler from subclass
        handler = self.get_request_handler()

        # Create and start server
        try:
            # Bind to all interfaces
            self.ip_addresses = self.get_all_ips()
            self.server = ThreadedHTTPServer(('0.0.0.0', self.port),
                                             handler)

            # Start server in background thread
            server_thread = threading.Thread(
                target=self.server.serve_forever)
            server_thread.daemon = True
            server_thread.start()

            # Display access options
            if not self.quiet:
                self._display_access_info()

            # Return the primary URL (first IP)
            index_path = self.get_index_path()
            return f"http://{self.ip_addresses[0][1]}:{self.port}{index_path}"

        except Exception as e:
            if not self.quiet:
                print(f"\nError starting HTTP server: {e}")
            return None

    def _display_access_info(self):
        """Display server access information."""
        hostname = self.get_fqdn()
        server_name = self.get_server_name()
        index_path = self.get_index_path()

        print(f"\n{server_name} started.")

        # Direct access via public IPs
        print("\nDirect access (if network allows):")
        for iface, ip in self.ip_addresses:
            url = f"http://{ip}:{self.port}{index_path}"
            if iface:
                print(f"  - {iface}: {url}")
            else:
                print(f"  - {url}")

        # SSH tunnel access
        print("\nSSH tunnel access:")
        print("  Create the SSH tunnel using a new terminal:")
        print("    ~~~")
        print(f"    ssh -L {self.port}:localhost:{self.port} {hostname}")
        print("    ~~~")
        print("  Open this URL in your browser:")
        print("    ~~~")
        print(f"    http://localhost:{self.port}{index_path}")
        print("    ~~~")

        print("\nPress Ctrl+C to stop the server and exit.")

    def stop(self):
        """Stop the HTTP server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()

class DynamicHttpServer(HttpServer):
    """HTTP server that dynamically generates HTML from SQLite."""

    def __init__(self, conf, pulp_stats, dynflow_stats, quiet=False,
                 log_callback=None):
        """Initialize dynamic HTTP server.

        Args:
            conf: Configuration object with args, settings, and sos info
            pulp_stats: Pre-computed pulp execution statistics
            dynflow_stats: Pre-computed dynflow execution statistics
            quiet: If True, suppress output messages
            log_callback: Optional callback function for logging messages
        """
        super().__init__(conf.args.output_path, quiet)
        self.conf = conf
        self.pulp_total_exectime = pulp_stats
        self.dynflow_total_exectime = dynflow_stats
        self.log_callback = log_callback

        # Initialize Jinja2 Environment
        template_dir = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "templates"
        )
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True
        )

    def generate_tasks_html(self):
        """Generate tasks HTML dynamically from SQLite database.

        Creates a new database connection for thread safety.

        Returns:
            str: Rendered HTML content
        """
        # Create thread-local database connection
        db = OutputSQLite(self.conf)
        data_provider = BaseDataProvider(db, self.conf)

        # Copy pre-computed stats to thread-local data provider
        data_provider.pulp_total_exectime = self.pulp_total_exectime
        data_provider.dynflow_plans_exectime = {}
        data_provider.pulp_plans_exectime = {}

        try:
            # Get tasks data
            rows = data_provider.get_tasks_flat_list(
                self.conf.args.showall
            )

            # Prepare template context
            context = {
                "rows": rows,
                "dynflow_total_exectime": self.dynflow_total_exectime,
                "pulp_total_exectime": sorted(
                    self.pulp_total_exectime.items(),
                    key=lambda item: item[1],
                    reverse=True
                )[:5],
                "sos": self.conf.sos,
            }

            # Render template
            template = self.jinja_env.get_template("tasks.html")
            return template.render(context)
        finally:
            # Close thread-local database connection
            db.close()

    def generate_actions_html(self, plan_uuid):
        """Generate actions HTML dynamically for a specific plan.

        Args:
            plan_uuid: The execution plan UUID

        Returns:
            str: Rendered HTML content
        """
        # Create thread-local database connection
        db = OutputSQLite(self.conf)

        try:
            # Fetch steps for this plan using shared query
            step_rows = ActionQueries.get_steps_for_plan(db, plan_uuid)
            steps = FormatHelpers.format_steps_with_json(
                step_rows,
                self.conf.args.showall
            )

            # Fetch actions for this plan using shared query
            rows = ActionQueries.get_actions_for_plan(db, plan_uuid)

            data = []
            for r in rows:
                if not self.conf.args.showall and r[8] == "success":
                    continue

                r = list(r)
                # Remove old single execution_time field
                del r[15]

                # Format JSON fields using shared helper
                r[5] = FormatHelpers.show_json(r[5])  # data
                r[6] = FormatHelpers.show_json(r[6])  # input
                r[7] = FormatHelpers.show_json(r[7])  # output

                # Attach steps to this action
                plan_uuid_key = r[1]
                action_id_key = r[0]
                if (plan_uuid_key in steps and
                        action_id_key in steps[plan_uuid_key]):
                    r.append(steps[plan_uuid_key][action_id_key])
                else:
                    r.append([])

                data.append(r)

            if not data:
                return "<html><body><h1>No actions found for this plan</h1></body></html>"

            # Build action hierarchy
            root_actions, child_actions, actions_by_id = (
                ActionHierarchy.build_hierarchy(data)
            )

            # Prepare template context
            context = {
                "root_actions": root_actions,
                "child_actions": child_actions,
                "label": data[0][9] if data else "",
                "execution_plan_uuid": plan_uuid,
                "caller_execution_plan_id": data[0][11] if data else "",
                "pulp_exectime": [],
                "dynflow_exectime": [],
                "sos": self.conf.sos,
            }

            # Render template
            template = self.jinja_env.get_template("actions.html")
            return template.render(context)
        finally:
            # Close thread-local database connection
            db.close()
    def get_server_name(self):
        """Override to provide server name."""
        return "HTTP Server (Dynamic Mode)"

    def get_index_path(self):
        """Override to use root path instead of index.html."""
        return "/"

    def get_request_handler(self):
        """Get custom request handler for dynamic content generation."""
        server_instance = self

        class DynamicRequestHandler(http.server.SimpleHTTPRequestHandler):
            """Custom HTTP request handler for dynamic content."""

            def do_GET(self):
                """Handle GET requests."""
                from urllib.parse import urlparse, parse_qs

                # Parse URL and query parameters
                parsed_url = urlparse(self.path)
                query_params = parse_qs(parsed_url.query)

                # Check if this is a request for actions page
                if 'plan_uuid' in query_params and parsed_url.path == '/':
                    plan_uuid = query_params['plan_uuid'][0]
                    try:
                        html_content = (
                            server_instance.generate_actions_html(plan_uuid)
                        )

                        # Send response
                        self.send_response(200)
                        self.send_header(
                            'Content-type',
                            'text/html; charset=utf-8'
                        )
                        self.send_header(
                            'Content-Length',
                            len(html_content.encode('utf-8'))
                        )
                        self.end_headers()
                        self.wfile.write(html_content.encode('utf-8'))
                    except Exception as e:
                        # Send error response
                        error_msg = f"Error generating actions page: {str(e)}"
                        self.send_response(500)
                        self.send_header('Content-type', 'text/plain')
                        self.end_headers()
                        self.wfile.write(error_msg.encode('utf-8'))

                elif self.path == '/' or self.path == '/index.html':
                    # Generate tasks HTML dynamically
                    try:
                        html_content = server_instance.generate_tasks_html()

                        # Send response
                        self.send_response(200)
                        self.send_header(
                            'Content-type',
                            'text/html; charset=utf-8'
                        )
                        self.send_header(
                            'Content-Length',
                            len(html_content.encode('utf-8'))
                        )
                        self.end_headers()
                        self.wfile.write(html_content.encode('utf-8'))
                    except Exception as e:
                        # Send error response
                        error_msg = f"Error generating page: {str(e)}"
                        self.send_response(500)
                        self.send_header('Content-type', 'text/plain')
                        self.end_headers()
                        self.wfile.write(error_msg.encode('utf-8'))
                else:
                    # Serve static files normally (CSS, JS, etc.)
                    super().do_GET()

            def log_message(self, format, *args):
                """Log HTTP requests."""
                message = format % args
                # Send to callback if available
                if server_instance.log_callback:
                    server_instance.log_callback(
                        f"{self.address_string()} - {message}"
                    )
                # Also print to console if not quiet
                if not server_instance.quiet:
                    super().log_message(format, *args)

        return DynamicRequestHandler
