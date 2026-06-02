"""Centralized theme and color definitions for text UI."""

# Color Palette
# Using CSS variable names for consistency with HTML interface
COLORS = {
    # Primary colors
    "primary": "#c44336",           # Foreman orange (main brand color)
    "primary_dark": "#a83731",      # Darker orange for hover/active
    "primary_light": "#d9564a",     # Lighter orange

    # Semantic colors
    "success": "#3f9c35",           # Green for success states
    "warning": "#ec7a08",           # Orange for warnings
    "error": "#c9190b",             # Red for errors
    "info": "#0088ce",              # Blue for informational

    # State colors
    "pending": "#ec7a08",           # Orange
    "skipped": "#f0ab00",           # Yellow
    "suspended": "#f0ab00",         # Yellow

    # Text colors
    "text_primary": "white",        # Main text
    "text_secondary": "#72767b",    # Secondary text
    "text_muted": "dim",            # Dimmed text

    # Accent and highlights
    "accent": "cyan",               # Accent color for titles/highlights
    "highlight": "yellow",          # For emphasized items

    # Background hints (using Textual's built-in)
    "bg_panel": "$panel",
    "bg_surface": "$surface",
    "bg_boost": "$boost",
}

# Style presets for common use cases
STYLES = {
    # Headers and titles
    "title": "bold cyan",
    "subtitle": "cyan",
    "section_title": "bold cyan",

    # Interactive elements
    "button_label": "bold",
    "link": "underline cyan",

    # Status and state
    "success_text": "green",
    "warning_text": "#ec7a08",
    "error_text": "red",
    "info_text": "cyan",

    # Data display
    "key": "cyan bold",             # For key:value pairs
    "value": "white",
    "label": "yellow",              # For labels/tags
    "highlight": "yellow",          # For emphasized items

    # Special
    "dim": "dim",
    "bold": "bold",
    "reverse": "reverse",
}

# Border styles
BORDERS = {
    "default": "solid $primary",
    "panel": "solid $primary",
    "modal": "thick $primary",
    "highlight": "solid cyan",
}

# Spacing standards (in cells)
# Use these constants for consistent spacing across all widgets
SPACING = {
    "padding": {
        "none": "0",           # No padding - for borders/frames
        "normal": "1",         # Standard padding - for containers with content
        "dialog": "1 2",       # Dialog/modal padding - more horizontal space
    },
    "margin": {
        "none": "0",           # No margin
        "vertical": "1 0",     # Vertical spacing between sections (most common)
        "horizontal": "0 1",   # Horizontal spacing (buttons, etc.)
        "top": "1 0 0 0",      # Top margin only
    },
}


def get_color(name: str) -> str:
    """Get color value by name.

    Args:
        name: Color name from COLORS dict

    Returns:
        Color value string
    """
    return COLORS.get(name, "white")


def get_style(name: str) -> str:
    """Get style preset by name.

    Args:
        name: Style name from STYLES dict

    Returns:
        Style string
    """
    return STYLES.get(name, "")


def get_border(name: str = "default") -> str:
    """Get border style by name.

    Args:
        name: Border name from BORDERS dict

    Returns:
        Border style string
    """
    return BORDERS.get(name, BORDERS["default"])
