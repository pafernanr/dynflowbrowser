# HTTP Server Access Modal - Updates

## Changes Summary

### 1. Context-Aware URLs
The modal now displays different URLs based on which screen it was opened from:

**From Tasks Screen (TasksScreen):**
- URLs point to root: `http://<IP>:<PORT>/`
- Generic task list view

**From Actions Screen (ActionsScreen):**
- URLs include plan_uuid parameter: `http://<IP>:<PORT>/?plan_uuid=<PLAN_UUID>`
- Direct link to specific task's actions/steps

### 2. HttpdInfoScreen Synchronization
The HTTPD info screen now detects when the server was started externally (e.g., from the modal):

**New Method: `_sync_external_server()`**
- Detects server running in `app.httpd_server`
- Updates local state (`self.server_running = True`)
- Fetches and displays server connection information
- Updates UI elements (status message, buttons, logs)
- Logs: "HTTP Server detected (started externally)"

**Updated Method: `on_show()`**
- Checks global server state on screen visibility
- Calls `_sync_external_server()` if server started externally
- Ensures UI always reflects current server state

## Implementation Details

### File: `dynflowbrowser/lib/ui/text/app.py`

#### HttpdAccessModal Class
```python
def __init__(self, conf, plan_uuid=None, **kwargs):
    """Initialize HTTP access modal.
    
    Args:
        conf: Configuration object
        plan_uuid: Optional plan UUID for actions screen
        **kwargs: Additional keyword arguments
    """
    super().__init__(**kwargs)
    self.conf = conf
    self.plan_uuid = plan_uuid  # NEW
    self.server_started = False
```

#### URL Construction in `_show_access_info()`
```python
# Build URL path based on plan_uuid
url_path = f"/?plan_uuid={self.plan_uuid}" if self.plan_uuid else "/"

# Direct HTTP Access section
for iface, ip in ip_addresses:
    url = f"http://{ip}:{port}{url_path}"  # Uses context-aware path
    ...

# SSH Tunnel Access section
ssh_text.append(f"     http://localhost:{port}{url_path}\n", style="bold")
```

#### TasksScreen
```python
def action_show_httpd_modal(self) -> None:
    """Show HTTP server access modal."""
    self.app.push_screen(HttpdAccessModal(self.conf, plan_uuid=None))
```

#### ActionsScreen
```python
def action_show_httpd_modal(self) -> None:
    """Show HTTP server access modal."""
    self.app.push_screen(HttpdAccessModal(self.conf, plan_uuid=self.plan_uuid))
```

### File: `dynflowbrowser/lib/ui/text/httpd_info.py`

#### Updated `on_show()` Method
```python
def on_show(self) -> None:
    """Called when screen becomes visible."""
    # Check global server state (in case it was started from modal)
    server_running = (
        hasattr(self.app, 'httpd_server')
        and self.app.httpd_server is not None
    )

    # If server was started externally, update our state
    if server_running and not self.server_running:
        self._sync_external_server()

    # Update tip message based on server state
    esc_tip = self.query_one("#server-esc-tip", Static)
    if self.server_running:
        esc_tip.update(
            "Press [bold cyan]ESC[/bold cyan] to use Terminal Browser "
            "(server keeps running)"
        )
    else:
        esc_tip.update("HTTPD is not required for Terminal Browser")
```

#### New `_sync_external_server()` Method
```python
def _sync_external_server(self) -> None:
    """Sync state when server was started externally (e.g., from modal)."""
    if not hasattr(self.app, 'httpd_server') or not self.app.httpd_server:
        return

    logs = self.query_one("#server-logs", RichLog)
    logs.write("[bold green]HTTP Server detected (started externally)[/bold green]")

    # Update server info
    self.server_info = {
        'ip_addresses': self.app.httpd_server.get_all_ips(),
        'port': self.app.httpd_server.port,
        'hostname': self.app.httpd_server.get_fqdn(),
    }
    self._update_display()
    self.server_running = True

    # Update status message
    status_msg = self.query_one("#server-status-msg", Static)
    status_msg.update(
        "Press [bold cyan](s)[/bold cyan] to stop the server"
    )

    # Show ESC tip
    esc_tip = self.query_one("#server-esc-tip", Static)
    esc_tip.update(
        "Press [bold cyan]ESC[/bold cyan] to use Terminal Browser "
        "(server keeps running)"
    )
```

## User Experience Improvements

### Before
1. URLs always pointed to `/` regardless of context
2. HttpdInfoScreen didn't reflect server started from modal
3. User had to manually navigate to task actions after opening HTTP link

### After
1. **Tasks Screen → (l)**: URLs point to `/` (task list)
2. **Actions Screen → (l)**: URLs point to `/?plan_uuid=<UUID>` (specific task)
3. **HttpdInfoScreen**: Automatically detects and displays externally-started server
4. User gets direct link to relevant view based on current context

## Testing Scenarios

### Scenario 1: Start Server from Modal (Tasks Screen)
1. User is in Tasks list
2. Press `(l)` → Modal opens
3. Press `(y)` → Server starts
4. URLs show: `http://<IP>:<PORT>/`
5. Navigate to HTTPD screen → Shows "HTTP Server detected (started externally)"

### Scenario 2: Start Server from Modal (Actions Screen)
1. User is viewing actions for a specific task
2. Press `(l)` → Modal opens
3. Press `(y)` → Server starts
4. URLs show: `http://<IP>:<PORT>/?plan_uuid=abc123...`
5. Opening URL goes directly to that task's actions

### Scenario 3: Check Running Server
1. Server already running (started from modal)
2. Navigate to HTTPD screen
3. Screen detects server and displays connection info
4. Button shows "Start/Stop" (not stuck on "Start")
