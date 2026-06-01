# DynflowBrowser

**Interactive browser for Dynflow task execution data from Red Hat Satellite sosreports**

DynflowBrowser provides powerful interfaces to analyze Foreman/Satellite task execution:
- **Terminal Browser**: Fast, keyboard-driven TUI for console-based analysis
- **HTTPD Service**: Web interface accessible from any browser

## Features

### 🚀 Performance & Efficiency
- **100x faster** than original [dynflowparser](https://github.com/pafernanr/dynflowparser) with optimized CSV parsing (pandas) and SQLite operations
- WAL mode and compound indexes for blazing-fast queries
- Smart filtering: only failed tasks loaded by default (use `-a` for all)

### 🖥️ Terminal Browser
- Interactive Textual-based TUI with full keyboard navigation
- Real-time task browsing without starting the HTTPD server
- Expandable/collapsible task hierarchies
- Auto-expansion of failed actions and steps for quick troubleshooting
- Toggle views: Task Action/ID ↔ Label/UUID
- Stats panel with Top Dynflow and Pulp metrics

### 🌐 HTTPD Service
- Dynamic page generation
- Manual start/stop control
- Share access quickly:
  - Network interface detection with direct HTTP access URLs
  - SSH tunnel support for remote access
- Server keeps running while browsing terminal interface
- Responsive full-width layout with improved readability

### 📊 Smart Analysis
- **Dynflow and Pulp Stats**: Top used classes by ExecTime or by Count
- **Error Navigation**: Failed actions & steps automatically expanded
- **System Context**: Header shows hostname, timezone, Satellite version, RAM, CPU, tuning profile
- **Timezone Support**: Dynflow and Pulp UTC dates automatically converted to sosreport timezone
- **Readable Formatting**: Indented fields for Actions & Steps with syntax highlighting

### TODO
- **Searchbox**: Allow to filter and search
- **Liveconnect**: Browse a live Foreman PostgreSQL

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
- Required libraries:
  - Jinja2
  - pandas
  - pytz
  - textual (for terminal UI)


## Exporting Tasks from Foreman Database

For systems where sosreport doesn't include dynflow data (size limitations):

```bash
# Run on the Satellite server
dynflowbrowser-export-tasks

# Options:
#  -d DAYS    Number of days to export (default: 14)
#  -f FILTER  SQL filter query, e.g: "label LIKE '%Manifest%'"
#  -o PATH    Output directory (default: /tmp)
```

Creates a compressed export file that can be analyzed with DynflowBrowser.

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
