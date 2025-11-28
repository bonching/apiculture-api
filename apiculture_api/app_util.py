from bson import ObjectId

class AppUtil:
    def convert_objectids(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, dict):
            return {'id' if key == '_id' else key: self.convert_objectids(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self.convert_objectids(item) for item in obj]
        return obj