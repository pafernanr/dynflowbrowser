# DynflowBrowser

Interactive browser for analyzing Dynflow task execution data from Red Hat Satellite sosreports.

## Overview

DynflowBrowser provides two interfaces for analyzing Foreman/Satellite task execution:

- **Terminal Browser**: Fast keyboard-driven TUI for console-based analysis
- **HTTPD Service**: Web interface accessible from any browser

- HTTPD Service can be started in background while using the Terminal Browser.
- Share HTTP or SSH tunnel access with colleagues to dig into the same Dynflow data.

## Key Features

- Fast CSV parsing with pandas and optimized SQLite operations
- Filter tasks by state, result, search queries, or time range
- Expandable task hierarchies with automatic error expansion
- Dynflow and Pulp execution statistics
- Timezone-aware date conversion. Dynflow and Pulp UTC converted to sosreport TZ.
- System context display (hostname, version, CPU, RAM, tuning)

## Installation

### Using pip
```bash
pip install dynflowbrowser
```

### Using prebuilt packages
Download from [Latest Release](https://github.com/pafernanr/dynflowbrowser/releases/latest)

## Requirements

- Python 3.6+
- Jinja2, pandas, pytz, textual

## Usage

### Basic usage
```bash
# Analyze current directory sosreport
dynflowbrowser

# Analyze specific sosreport
dynflowbrowser /path/to/sosreport

# Filter by state and result
dynflowbrowser --state stopped --result error

# Filter by time range
dynflowbrowser --task-days 7

# Complex search queries
dynflowbrowser --search="label ~ Sync AND result = error"
dynflowbrowser --search="state = stopped AND result != success"
```

### Search Query Syntax

Supports foreman-rake compatible queries with operators:
- Comparison: `=`, `!=`, `>`, `<`, `>=`, `<=`
- Pattern matching: `~` (contains), `!~` (not contains)
- Logical: `AND`, `OR`

Examples:
```bash
--search="result != success"
--search="label ~ Manifest"
--search="state = stopped AND result = error"
```

### Terminal Interface

Navigate with keyboard shortcuts:
- `t` - Toggle between Action/ID and Label/UUID views
- `s` - Toggle Dynflow/Pulp statistics panel
- `h` - Show HTTP access information
- `Enter` - Expand/collapse task details
- `d` - Show action/step details popup
- `q` or `Esc` - Quit (with confirmation)

### Web Interface

Start the HTTPD service from the welcome screen or terminal browser:
- Direct HTTP access on detected network interfaces
- SSH tunnel support for remote access
- Responsive layout with collapsible task hierarchies

## Exporting Tasks from Foreman Database

For systems where sosreport doesn't include dynflow data:

```bash
# Run on the Satellite server
dynflowbrowser-export-tasks

# Options:
#  -d DAYS    Number of days to export (default: 14)
#  -f FILTER  SQL filter query
#  -o PATH    Output directory (default: /tmp)
```

Creates a compressed export file compatible with DynflowBrowser.

## Screenshots

| Tasks list | Task details | Terminal |
| --- | --- | --- |
| ![](https://raw.githubusercontent.com/pafernanr/dynflowbrowser/refs/heads/main/docs/files/_screenshot1.png) | ![](https://raw.githubusercontent.com/pafernanr/dynflowbrowser/refs/heads/main/docs/files/_screenshot2.png) | ![](https://raw.githubusercontent.com/pafernanr/dynflowbrowser/refs/heads/main/docs/files/_screenshot3.png) |

## Project Structure

```
dynflowbrowser/
├── bin/              # Entry point scripts
├── lib/
│   ├── ui/
│   │   ├── text/    # Terminal UI (Textual framework)
│   │   ├── httpd/   # Dynamic HTTP server
│   │   └── shared/  # Shared components
│   ├── configuration.py
│   ├── inputdynflow.py
│   └── outputsqlite.py
└── plugins/          # Plugin system
```
