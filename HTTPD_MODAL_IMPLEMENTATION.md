# HTTP Server Access Modal - Implementation Summary

## Overview
Added a new keyboard shortcut `(l)` to the Terminal interface that opens a modal window for HTTP server access information.

## Changes Made

### File Modified
- `dynflowbrowser/lib/ui/text/app.py`

### New Features

#### 1. New Modal Class: `HttpdAccessModal`
A modal screen that provides two different views:

**When HTTP Server is Stopped:**
- Displays a prompt asking if the user wants to start the server
- Shows options: `(y)` for Yes, `(n)` for No
- Pressing `(y)` starts the HTTP server
- Pressing `(n)` or `ESC` closes the modal

**When HTTP Server is Running:**
- Shows **Direct HTTP Access** section with all available network interfaces and IPs
- Shows **SSH Tunnel Access** section with:
  - Command to create SSH tunnel
  - Local browser URL to access after tunnel is established

#### 2. Keyboard Bindings Added

**TasksScreen (Tasks List):**
```python
Binding("l", "show_httpd_modal", "HTTP Access", show=True)
```

**ActionsScreen (Actions/Steps View):**
```python
Binding("l", "show_httpd_modal", "HTTP Access", show=True)
```

#### 3. Action Methods
Added `action_show_httpd_modal()` to both screens:
- Creates and pushes the `HttpdAccessModal` to the screen stack
- Modal automatically detects server state and shows appropriate content

#### 4. Modal Functionality

**Key Methods:**

- `_update_content()`: Checks server state and updates modal display
- `_show_start_prompt()`: Displays prompt to start server with Yes/No options
- `_show_access_info()`: Displays connection information when server is running
- `action_start_server()`: Starts the HTTP server and updates display
- `action_dismiss()`: Closes the modal (ESC, q, or n)

**Server Startup Process:**
1. Computes execution statistics (Pulp and Dynflow)
2. Copies static assets
3. Creates `DynamicHttpServer` instance
4. Starts server in background thread
5. Updates modal to show access information

#### 5. CSS Styling
Added modal-specific styles:
```css
HttpdAccessModal {
    align: center middle;
}

#httpd_modal_container {
    width: 80;
    height: auto;
    background: $surface;
    border: thick $primary;
    padding: 1;
}

#httpd_modal_title {
    background: $boost;
    color: $text;
    padding: 1;
    text-style: bold;
}

#httpd_modal_content {
    padding: 2;
    height: auto;
    max-height: 30;
}
```

## User Workflow

### Scenario 1: Server Not Running
1. User presses `(l)` in Tasks or Actions screen
2. Modal opens showing: "The HTTP server is currently stopped. Would you like to start it?"
3. User can:
   - Press `(y)` → Server starts, modal updates to show access info
   - Press `(n)` or `ESC` → Modal closes

### Scenario 2: Server Already Running
1. User presses `(l)` in Tasks or Actions screen
2. Modal opens immediately showing:
   - Direct HTTP Access URLs for all network interfaces
   - SSH Tunnel setup instructions
3. User presses `ESC` to close

## Integration Points

- Uses existing `DynamicHttpServer` from `dynflowbrowser.lib.ui.httpd.server`
- Uses existing `HttpdOutput` for statistics computation
- Server instance stored in `self.app.httpd_server` (shared across screens)
- Modal checks server state via `hasattr(self.app, 'httpd_server')`

## Benefits

1. **Accessibility**: Quick access to HTTP server info from anywhere in the TUI
2. **User-Friendly**: Clear prompts and instructions
3. **Consistent**: Available in both Tasks and Actions screens
4. **Non-Intrusive**: Modal design doesn't disrupt workflow
5. **Informative**: Shows all connection methods (direct and SSH tunnel)

## Testing

All implementation checks passed:
- ✓ HttpdAccessModal class defined
- ✓ TasksScreen has (l) binding
- ✓ ActionsScreen has (l) binding
- ✓ action_show_httpd_modal methods implemented
- ✓ Server start/stop logic
- ✓ Access info display logic
- ✓ CSS styling
- ✓ Python syntax valid
