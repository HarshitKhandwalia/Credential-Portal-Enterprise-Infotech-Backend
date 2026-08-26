import re
from rest_framework import serializers
from .models import EmployeeCredential

class EmployeeCredentialSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
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
        if not value:
            return None
        
        normalized_email = value.strip().lower()
        if not normalized_email:
            return None

        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, normalized_email):
            raise serializers.ValidationError("Enter a valid email address.")
            
        return normalized_email

    def validate_phone(self, value):
        if not value:
            return None

        cleaned_phone = re.sub(r'[\s\-\(\)]', '', value)
        if not cleaned_phone:
            return None

        phone_regex = r'^\+?[1-9]\d{6,14}$'
        if not re.match(phone_regex, cleaned_phone):
            raise serializers.ValidationError("Enter a valid phone number with country code (e.g., +917981557871).")

        return cleaned_phone

    def validate(self, attrs):
        email = attrs.get('email')
        phone = attrs.get('phone')

        if not email and not phone:
            raise serializers.ValidationError(
                {"non_field_errors": ["At least one contact method (Email or Phone Number) is required."]}
            )

        return attrs