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
            return {('_id' if key == 'id' else key): (self.str_to_objectid(value) if key == 'id' else value) for key, value in obj.items()}
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