import re

from rest_framework import serializers

from .models import Chapter, EmployeeCredential, ScanLog, Session, SessionAttendance


class ChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = ['id', 'name', 'description', 'is_active', 'created_at']
        read_only_fields = ['created_at']


class SessionSerializer(serializers.ModelSerializer):
    chapter_name = serializers.CharField(source='chapter.name', read_only=True)

    class Meta:
        model = Session
        fields = [
            'id',
            'chapter',
            'chapter_name',
            'title',
            'starts_at',
            'ends_at',
            'status',
        ]
        read_only_fields = ['chapter']

    def validate(self, attrs):
        starts_at = attrs.get('starts_at', getattr(self.instance, 'starts_at', None))
        ends_at = attrs.get('ends_at', getattr(self.instance, 'ends_at', None))
        if starts_at and ends_at and ends_at <= starts_at:
            raise serializers.ValidationError(
                {'ends_at': 'ends_at must be after starts_at.'}
            )
        return attrs


class EmployeeCredentialSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    credential = serializers.CharField(read_only=True)
    chapter = serializers.PrimaryKeyRelatedField(
        queryset=Chapter.objects.all(),
        required=False,
        allow_null=False,
    )
    chapter_name = serializers.CharField(source='chapter.name', read_only=True, default=None)
    formatted_created_at = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeCredential
        fields = [
            'id',
            'name',
            'membership_id',
            'credential',
            'status',
            'email',
            'phone',
            'primary_credential',
            'secondary_credential',
            'chapter',
            'chapter_name',
            'created_at',
            'formatted_created_at',
            'is_attended',
            'attended_at',
        ]
        read_only_fields = ['credential', 'is_attended', 'attended_at']

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
            raise serializers.ValidationError(
                "Enter a valid phone number with country code (e.g., +917981557871)."
            )

        return cleaned_phone

    def validate(self, attrs):
        email = attrs.get('email', getattr(self.instance, 'email', None) if self.instance else None)
        phone = attrs.get('phone', getattr(self.instance, 'phone', None) if self.instance else None)

        if self.instance is None:
            if not attrs.get('email') and not attrs.get('phone'):
                raise serializers.ValidationError(
                    {"non_field_errors": ["At least one contact method (Email or Phone Number) is required."]}
                )
            if 'chapter' not in attrs or attrs.get('chapter') is None:
                raise serializers.ValidationError({'chapter': 'Chapter is required.'})
        else:
            # On update, only enforce contact if both would become empty.
            if email is None and phone is None:
                raise serializers.ValidationError(
                    {"non_field_errors": ["At least one contact method (Email or Phone Number) is required."]}
                )

        return attrs


class EmployeeSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeCredential
        fields = ['id', 'name', 'membership_id', 'credential', 'email', 'phone']


class SessionAttendanceSerializer(serializers.ModelSerializer):
    employee = EmployeeSummarySerializer(read_only=True)

    class Meta:
        model = SessionAttendance
        fields = ['id', 'employee', 'scanned_at', 'device_id']


class SessionReportSerializer(serializers.Serializer):
    session = SessionSerializer()
    expected_count = serializers.IntegerField()
    attended_count = serializers.IntegerField()
    absent_count = serializers.IntegerField()
    attended = EmployeeSummarySerializer(many=True)
    absent = EmployeeSummarySerializer(many=True)


class ScanResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    employee = EmployeeCredentialSerializer(required=False, allow_null=True)


class ScanLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanLog
        fields = ['id', 'credential', 'status', 'device_id', 'session', 'scanned_at']
