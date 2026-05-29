# DynflowBrowser

**Interactive browser for Dynflow task execution data from Red Hat Satellite sosreports**

DynflowBrowser provides powerful interfaces to analyze Foreman/Satellite task execution:
- **Terminal Browser**: Fast, keyboard-driven TUI for console-based analysis
- **HTTPD Service**: Web interface accessible from any browser

## Features

### 🚀 Performance & Efficiency
- **5-10x faster** than original version with optimized CSV parsing (pandas) and SQLite operations
- WAL mode and compound indexes for blazing-fast queries
- Smart filtering: only failed tasks loaded by default (use `-a` for all)

### 🖥️ Terminal Browser
- Interactive Textual-based TUI with full keyboard navigation
- Real-time task browsing without starting a server
- Expandable/collapsible task hierarchies (arrow keys)
- Auto-expansion of failed actions and steps for quick troubleshooting
- Toggle views: Task Action/ID ↔ Label/UUID (press `t`)
- Stats panel with Top Dynflow and Pulp metrics (press `s`)

### 🌐 HTTPD Service
- On-demand page generation (no disk writes)
- Manual start/stop control (press `s` in HTTPD screen)
- Network interface detection with direct HTTP access URLs
- SSH tunnel support for remote access
- Server keeps running while browsing terminal interface
- Responsive full-width layout with improved readability

### 📊 Smart Analysis
- **Error Navigation**: Failed actions & steps automatically expanded
- **System Context**: Header shows hostname, timezone, Satellite version, RAM, CPU, tuning profile
- **Timezone Support**: UTC dates automatically converted to sosreport timezone
- **Readable Formatting**: Indented fields for Actions & Steps with syntax highlighting

## Installation

### Using pip
```bash
pip install dynflowbrowser
```

### Using prebuilt packages
Download from [Latest Release](https://github.com/pafernanr/dynflowbrowser/releases/latest)

### From source
```bash
git clone https://github.com/pafernanr/dynflowbrowser.git
cd dynflowbrowser
pip install -e .
```

## Requirements

- Python 3.6+
- Required libraries:
  - Jinja2
  - pandas
  - pytz
  - textual (for terminal UI)

## Quick Start

### Default: Welcome Screen (Interactive Mode Selection)
```bash
dynflowbrowser /path/to/sosreport
```
Navigate with:
- **Arrow keys** / **Tab**: Select interface mode
- **Enter** / **t**: Terminal Browser
- **h**: HTTPD Service

### Terminal Browser (Direct Launch)
```bash
dynflowbrowser --text /path/to/sosreport
```

Keyboard shortcuts:
- **Arrow keys**: Navigate tasks
- **Enter**: View task details
- **Left/Right**: Collapse/expand task hierarchies
- **t**: Toggle Task Action/ID ↔ Label/UUID view
- **s**: Show/hide stats panel
- **ESC**: Back to previous screen
- **q**: Quit

### HTTPD Service (Direct Launch)
```bash
dynflowbrowser --httpd /path/to/sosreport
```

In HTTPD screen:
- Press **s** to start/stop the server
- Press **ESC** to use Terminal Browser while server runs
- Server provides URLs for direct access and SSH tunnel instructions

### Remote Access via SSH Tunnel
When HTTPD server is running:
```bash
# On your local machine
ssh -L 8000:localhost:8000 satellite-hostname

# Then open in browser
http://localhost:8000/
```

## Usage Options

```bash
dynflowbrowser [OPTIONS] SOSREPORT_PATH
```

### Interface Options
- `--text`: Launch Terminal Browser directly
- `--httpd`: Launch HTTPD Service screen directly
- *(no flag)*: Show welcome screen with mode selection

### Filtering Options
- `-a, --showall`: Show all tasks (default: only failed tasks)
- `-f, --from DATE`: Parse tasks from this datetime
- `-t, --to DATE`: Parse tasks up to this datetime
- `-l, --last N`: Parse only last N days

### Advanced Options
- `-o, --output_path PATH`: Output directory (default: `./dynflowbrowser/`)
- `-n, --nosql`: Reuse existing SQLite database
- `-q, --quiet`: Suppress progress output
- `-d, --debug`: Enable debug mode

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

## Screenshots

### Welcome Screen
```
  _____              ______ _               ____
 |  __ \            |  ____| |             |  _ \
 | |  | |_   _ _ __ | |__  | | _____      _| |_) |_ __ _____      _____  ___ _ __
 | |  | | | | | '_ \|  __| | |/ _ \ \ /\ / /  _ <| '__/ _ \ \ /\ / / __|/ _ \ '__|
 | |__| | |_| | | | | |    | | (_) \ V  V /| |_) | | | (_) \ V  V /\__ \  __/ |
 |_____/ \__, |_| |_|_|    |_|\___/ \_/\_/ |____/|_|  \___/ \_/\_/ |___/\___|_|
          __/ |
         |___/

Select the Interface Mode:
    [ Terminal Browser ]  [ HTTPD Service ]
```

### Terminal Browser
- Task list with hierarchical view
- Expandable failed tasks showing actions and steps
- Real-time filtering and stats

### HTTPD Service
- Connection info (Direct HTTP / SSH Tunnel)
- Server control (Start/Stop)
- Live server logs

## Development

### Running Tests
```bash
pip install -r test-requirements.txt
pytest
```

### Code Style
```bash
flake8 dynflowbrowser/
```

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

GPLv3 - See [LICENSE](LICENSE) for details

## Author

Pablo Fernández Rodríguez

## Links

- **GitHub**: https://github.com/pafernanr/dynflowbrowser
- **Issues**: https://github.com/pafernanr/dynflowbrowser/issues
- **PyPI**: https://pypi.org/project/dynflowbrowser/

## Acknowledgments

Built with:
- [Textual](https://github.com/Textualize/textual) - Modern TUI framework
- [Jinja2](https://palletsprojects.com/p/jinja/) - Template engine
- [pandas](https://pandas.pydata.org/) - Data analysis
