"""Search query parser for foreman-rake compatible syntax."""
import re


class SearchParser:
    """Parse and evaluate foreman-rake search queries."""

    def __init__(self):
        """Initialize the search parser."""
        self.operators = {
            '=': lambda a, b: str(a).lower() == str(b).lower(),
            '!=': lambda a, b: str(a).lower() != str(b).lower(),
            '~': lambda a, b: str(b).lower() in str(a).lower(),
            '!~': lambda a, b: str(b).lower() not in str(a).lower(),
            '>': lambda a, b: a > b,
            '<': lambda a, b: a < b,
            '>=': lambda a, b: a >= b,
            '<=': lambda a, b: a <= b,
        }

    def parse(self, query):
        """Parse a search query string into conditions.

        Args:
            query: Search query string like 'result = error AND state != stopped'

        Returns:
            List of (field, operator, value, connector) tuples
        """
        if not query:
            return []

        # Split by AND/OR connectors
        # Pattern: field operator value [AND|OR]
        pattern = r'(\w+)\s*(=|!=|~|!~|>=|<=|>|<)\s*"([^"]*)"|(\w+)\s*(=|!=|~|!~|>=|<=|>|<)\s*(\S+)'

        conditions = []
        matches = list(re.finditer(pattern, query))

        for idx, match in enumerate(matches):
            # Extract field, operator, value
            if match.group(1):  # Quoted value
                field = match.group(1)
                operator = match.group(2)
                value = match.group(3)
            else:  # Unquoted value
                field = match.group(4)
                operator = match.group(5)
                value = match.group(6)

            # Check what comes AFTER this match for AND/OR connector
            connector = None
            if idx < len(matches) - 1:
                next_match = matches[idx + 1]
                between = query[match.end():next_match.start()].strip().upper()
                if 'AND' in between:
                    connector = 'AND'
                elif 'OR' in between:
                    connector = 'OR'

            conditions.append((field, operator, value, connector))

        return conditions

    def evaluate(self, conditions, row_data, headers):
        """Evaluate search conditions against a data row.

        Args:
            conditions: List of (field, operator, value, connector) tuples
            row_data: List of values for a single row
            headers: List of field names

        Returns:
            bool: True if row matches all conditions
        """
        if not conditions:
            return True

        result = None

        for idx, (field, operator, value, connector) in enumerate(conditions):
            # Get field value from row
            try:
                field_index = headers.index(field)
                field_value = row_data[field_index]
            except (ValueError, IndexError):
                # Field not found or index error
                condition_result = False
            else:
                # Apply operator
                op_func = self.operators.get(operator)
                if not op_func:
                    condition_result = False
                else:
                    try:
                        condition_result = op_func(field_value, value)
                    except Exception:
                        condition_result = False

            # Combine with previous result
            if idx == 0:
                # First condition
                result = condition_result
            else:
                # Use the connector from the PREVIOUS condition
                # (connector is stored with the condition it follows)
                prev_connector = conditions[idx - 1][3]
                if prev_connector == 'AND':
                    result = result and condition_result
                elif prev_connector == 'OR':
                    result = result or condition_result
                else:
                    # No connector specified, treat as AND (default)
                    result = result and condition_result

        return result if result is not None else True
