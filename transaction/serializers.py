from rest_framework import serializers
from bson import ObjectId

class ObjectIdField(serializers.Field):
    def to_representation(self, value):
        return str(value) 

    def to_internal_value(self, data):
        try:
            return ObjectId(str(data))
        except Exception:
            raise serializers.ValidationError("Invalid ObjectId")
    

class ReportQuerySerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=['count', 'amount'])
    mode = serializers.ChoiceField(choices=['daily', 'weekly', 'monthly'])
    merchantId =ObjectIdField(required=False)
