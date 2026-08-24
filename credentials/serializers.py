import re
from rest_framework import serializers
from .models import EmployeeCredential

class EmployeeCredentialSerializer(serializers.ModelSerializer):
    formatted_created_at = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeCredential
        fields = [
            'id', 'name', 'status', 'email', 'phone', 
            'primary_credential', 'secondary_credential', 
            'created_at', 'formatted_created_at'
        ]

    def get_formatted_created_at(self, obj):
        return obj.created_at.strftime("%m/%d/%Y, %I:%M %p")

    def validate_email(self, value):
        normalized_email = value.strip().lower()
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, normalized_email):
            raise serializers.ValidationError("Enter a valid email address.")
            
        return normalized_email

    def validate_phone(self, value):
        cleaned_phone = re.sub(r'[\s\-\(\)]', '', value)
        phone_regex = r'^\+?[1-9]\d{6,14}$'
        if not re.match(phone_regex, cleaned_phone):
            raise serializers.ValidationError("Enter a valid phone number with country code (e.g., +917981557871).")

        return cleaned_phone