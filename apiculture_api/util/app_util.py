import re
from datetime import datetime, timezone
from dateutil import parser

from bson import ObjectId
from bson.errors import InvalidId


class AppUtil:
    def objectid_to_str(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, dict):
            return {('id' if key == '_id' else key): (self.objectid_to_str(value) if key == '_id' else value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self.objectid_to_str(item) for item in obj]
        return obj

    def str_to_objectid(self, obj):
        if isinstance(obj, str):
            try:
                # Check if it's a valid 24-character hex string for ObjectId
                if len(obj) == 24 and all(c in '0123456789abcdefABCDEF' for c in obj):
                    return ObjectId(obj)
            except InvalidId:
                pass
            return obj  # Not a valid ObjectId string, return as-is
        elif isinstance(obj, dict):
            # Rename 'id' keys to '_id' and recurse on values
            return {key: (self.str_to_objectid(value) if key == '_id' else value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self.str_to_objectid(item) for item in obj]
        return obj  # Primitives unchanged

    def remove_id_key(self, obj):
        """
        Recursively removes any 'id' keys from dictionaries and nested structures.
        Leaves other types unchanged.
        """
        if isinstance(obj, dict):
            # Create a new dict without 'id' key, and recurse on remaining values
            return {key: self.remove_id_key(value) for key, value in obj.items() if key != 'id'}
        elif isinstance(obj, list):
            return [self.remove_id_key(item) for item in obj]
        return obj  # Primitives unchanged

    def fix_datetime(self, obj):
        """
        Recursively processes an object (dict/list) to convert 'datetime' string fields
        in ISO-like format to proper datetime objects for MongoDB insertion.
        Assumes UTC; leaves other types unchanged.
        """
        if isinstance(obj, dict):
            new_obj = {}
            for key, value in obj.items():
                if key == 'datetime' and isinstance(value, str):
                    # Parse ISO-like string to datetime (assumes UTC)
                    try:
                        # Handle the format 'YYYY-MM-DDTHH:MM:SS.mmm' (no timezone explicit)
                        parsed_dt = datetime.fromisoformat(
                            value.replace('Z', '+00:00') if value.endswith('Z') else value)
                        new_obj[key] = parsed_dt
                    except ValueError:
                        # If parsing fails, leave as string (or raise/log as needed)
                        new_obj[key] = value
                else:
                    new_obj[key] = self.fix_datetime(value)
            return new_obj
        elif isinstance(obj, list):
            return [self.fix_datetime(item) for item in obj]
        return obj

    def camel_to_snake_key(self, obj, convert_values=False):
        """
        Recursively converts CamelCase keys to snake_case in dictionaries and nested structures.

        Args:
            obj: The input object (dict, list, or primitive).
            convert_values (bool): If True, also convert string values that are keys (e.g., in lists of dicts).

        Returns:
            The modified object with converted keys.
        """
        if isinstance(obj, dict):
            new_obj = {}
            for key, value in obj.items():
                # Convert key
                snake_key = self.camel_to_snake(key)
                # Recurse on value
                new_value = self.camel_to_snake_key(value, convert_values) if convert_values or isinstance(value, (dict,
                                                                                                              list)) else value
                new_obj[snake_key] = new_value
            return new_obj
        elif isinstance(obj, list):
            return [self.camel_to_snake_key(item, convert_values) for item in obj]
        elif convert_values and isinstance(obj, str):
            # Optional: Convert string values if flagged (e.g., for key-like strings in lists)
            return self.camel_to_snake(obj)
        return obj

    def snake_to_camel_key(self, obj, convert_values=False):
        """
        Recursively converts snake_case keys to CamelCase in dictionaries and nested structures.

        Args:
            obj: The input object (dict, list, or primitive).
            convert_values (bool): If True, also convert string values that are keys.

        Returns:
            The modified object with converted keys.
        """
        if isinstance(obj, dict):
            new_obj = {}
            for key, value in obj.items():
                # Convert key
                camel_key = self.snake_to_camel(key)
                # Recurse on value
                new_value = self.snake_to_camel_key(value, convert_values) if convert_values or isinstance(value, (dict,
                                                                                                              list)) else value
                new_obj[camel_key] = new_value
            return new_obj
        elif isinstance(obj, list):
            return [self.snake_to_camel_key(item, convert_values) for item in obj]
        elif convert_values and isinstance(obj, str):
            # Optional: Convert string values if flagged
            return self.snake_to_camel(obj)
        return obj

    # Reusing the helper functions from before
    def camel_to_snake(self, name):
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def snake_to_camel(self, name):
        components = name.split('_')
        return components[0] + ''.join(x.capitalize() for x in components[1:])

    def time_ago(self, timestamp):
        """
        Convert a Unix timestamp to a relative time string like 'N seconds ago'.

        Args:
        timestamp (float or int): Unix timestamp (seconds since epoch).

        Returns:
        str: Relative time string.
        """
        now = datetime.now(timezone.utc)
        past = datetime.fromtimestamp(timestamp, timezone.utc)
        delta = now - past
        total_seconds = delta.total_seconds()

        if total_seconds < 1:
            return "just now"

        if total_seconds < 60:
            seconds = int(total_seconds)
            unit = "second" if seconds == 1 else "seconds"
            return f"{seconds} {unit} ago"

        elif total_seconds < 3600:
            minutes = int(total_seconds / 60)
            unit = "minute" if minutes == 1 else "minutes"
            return f"{minutes} {unit} ago"

        elif total_seconds < 86400:
            hours = int(total_seconds / 3600)
            unit = "hour" if hours == 1 else "hours"
            return f"{hours} {unit} ago"

        elif total_seconds < 7 * 86400:
            days = int(total_seconds / 86400)
            unit = "day" if days == 1 else "days"
            return f"{days} {unit} ago"

        else:
            weeks = int(total_seconds / (7 * 86400))
            unit = "week" if weeks == 1 else "weeks"
            return f"{weeks} {unit} ago"

    def convert_dict_str_to_utc_timestamp(data_dict, key):
        """
        Convert a specific dict value (datetime string) to UTC Unix timestamp (float).

        Args:
        data_dict (dict): Input dictionary.
        key (str): The key whose value (str) to convert.

        Returns:
        dict: Updated dict with the value as UTC timestamp (float).
        """
        if key not in data_dict or not isinstance(data_dict[key], str):
            print(f"Warning: Key '{key}' not found or not a string.")
            return data_dict

        date_str = data_dict[key]

        # Parse the string to a timezone-aware datetime (assumes UTC if no TZ specified)
        parsed_dt = parser.parse(date_str)
        if parsed_dt.tzinfo is None:
            # If naive, treat as UTC
            parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
        else:
            # Convert to UTC if in another timezone
            parsed_dt = parsed_dt.astimezone(timezone.utc)

        # Convert to timestamp and update dict
        timestamp = parsed_dt.timestamp()  # float; use int() for integer seconds
        data_dict[key] = timestamp

        return data_dict