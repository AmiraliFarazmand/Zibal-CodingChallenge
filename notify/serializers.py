from rest_framework import serializers
from bson import ObjectId

class ObjectIdField(serializers.Field):
    def to_representation(self, value):
        return str(value) 

    def to_internal_value(self, data):
        if not  ObjectId().is_valid(data):
            raise serializers.ValidationError("Invalid ObjectId")
        return data
    

class ResetPasswordRequestSerializer(serializers.Serializer):
    merchantId = ObjectIdField(required=True)
    channel = serializers.ChoiceField(choices=["sms", "email", "telegram"])
    lang = serializers.ChoiceField(choices=["fa", "en"], required=False, default=None)
