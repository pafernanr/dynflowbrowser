# DynflowBrowser

Interactive browser for analyzing Dynflow task execution data from TheForeman/Red Hat Satellite sosreports.

## Overview

- DynflowBrowser reads Dynflow csv files from a sosreport and saves the data to a SQLite file.
- The database is used to obtain Tasks, Actions and Steps details.
- Generates Dynflow and also Pulp statistics by execution time.
- There are available two interfaces for analyzing Dynflow execution:
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

## Screenshots

| Tasks list | Task details | Terminal |
| --- | --- | --- |
| ![](https://raw.githubusercontent.com/pafernanr/dynflowbrowser/refs/heads/main/docs/files/_screenshot1.png) | ![](https://raw.githubusercontent.com/pafernanr/dynflowbrowser/refs/heads/main/docs/files/_screenshot2.png) | ![](https://raw.githubusercontent.com/pafernanr/dynflowbrowser/refs/heads/main/docs/files/_screenshot3.png) |

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

```bash
usage: dynflowbrowser [-h] [-v] [--search SEARCH] [--state {paused,pending,planned,planning,running,stopped}]
                      [--result {error,pending,success,warning}] [--task-days TASK_DAYS] [-o OUTPUT_PATH]
                      [sosreport_path]

Get sosreport dynflow files and generates user friendly html pages for tasks, plans, actions and steps

positional arguments:
  sosreport_path        Path to sos report folder. Default is current path.

options:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  --search SEARCH       Search query using foreman-rake syntax. Supports operators: =, !=, ~, !~, >, <, >=, <= and connectors: AND,
                        OR
  --state {paused,pending,planned,planning,running,stopped}
                        Filter by task state. Valid: paused, pending, planned, planning, running, stopped
  --result {error,pending,success,warning}
                        Filter by task result. Valid: error, pending, success, warning
  --task-days TASK_DAYS
                        Import only tasks from last N days. Same as foreman-rake TASK_DAYS parameter.
  -o OUTPUT_PATH, --output_path OUTPUT_PATH
                        Write output to this path. Default is './dynflowbrowser/'.

Examples:
  # Combine state, result and time filters
  dynflowbrowser --state stopped --result error --task-days 10

  # Complex search query (AND / OR operators)
  dynflowbrowser --search="result != success" --task-days 3
  dynflowbrowser --search="label ~ Sync AND state = stopped AND result = error"
```

### Web Interface

Start the HTTPD service from the welcome screen or terminal browser:
- Direct HTTP access on detected network interfaces
- SSH tunnel support for remote access
- Responsive layout with collapsible task hierarchies

## Exporting Tasks from Foreman Database

For systems where `sos` is not installed or doesn't include dynflow data:

```bash
# Run on the Satellite server
dynflowbrowser-export-tasks

# Options:
#  -d DAYS    Number of days to export (default: 14)
#  -f FILTER  SQL filter query
#  -o PATH    Output directory (default: /tmp)
```

Creates a compressed export file compatible with DynflowBrowser.

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
