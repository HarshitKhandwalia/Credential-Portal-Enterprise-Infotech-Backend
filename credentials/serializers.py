import re

from rest_framework import serializers

from .models import (
    Chapter,
    EmployeeCredential,
    PaymentHistory,
    ScanLog,
    Session,
    SessionAttendance,
    Substitute,
    Template,
    Visitor,
)
from .utils import format_cycle_display


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


class RecurringSessionCreateSerializer(serializers.Serializer):
    """
    Create weekly sessions up front (same weekday as starts_at) until recurrence_end_date.
    Cap: 10 sessions.
    """

    title = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    recurrence_end_date = serializers.DateField()
    status = serializers.ChoiceField(
        choices=Session.STATUS_CHOICES,
        default='scheduled',
        required=False,
    )

    def validate(self, attrs):
        starts_at = attrs['starts_at']
        ends_at = attrs['ends_at']
        recurrence_end_date = attrs['recurrence_end_date']

        if ends_at <= starts_at:
            raise serializers.ValidationError(
                {'ends_at': 'ends_at must be after starts_at.'}
            )
        if recurrence_end_date < starts_at.date():
            raise serializers.ValidationError(
                {
                    'recurrence_end_date': (
                        'recurrence_end_date must be on or after the start date.'
                    )
                }
            )
        return attrs


class EmployeeCredentialSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    company_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    linkedin_url = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    website_url = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    credential = serializers.CharField(read_only=True)
    membership_id = serializers.CharField(read_only=True)
    profile_token = serializers.CharField(read_only=True)
    chapter = serializers.PrimaryKeyRelatedField(
        queryset=Chapter.objects.all(),
        required=False,
        allow_null=True,
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
            'profile_token',
            'status',
            'email',
            'phone',
            'company_name',
            'linkedin_url',
            'website_url',
            'primary_credential',
            'secondary_credential',
            'chapter',
            'chapter_name',
            'created_at',
            'formatted_created_at',
            'is_attended',
            'attended_at',
        ]
        read_only_fields = [
            'credential',
            'membership_id',
            'profile_token',
            'is_attended',
            'attended_at',
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
            raise serializers.ValidationError(
                "Enter a valid phone number with country code (e.g., +917981557871)."
            )

        return cleaned_phone

    def validate_company_name(self, value):
        if not value:
            return None
        cleaned = value.strip()
        return cleaned or None

    def validate_linkedin_url(self, value):
        if not value:
            return None
        cleaned = value.strip()
        return cleaned or None

    def validate_website_url(self, value):
        if not value:
            return None
        cleaned = value.strip()
        return cleaned or None

    def validate(self, attrs):
        email = attrs.get('email', getattr(self.instance, 'email', None) if self.instance else None)
        phone = attrs.get('phone', getattr(self.instance, 'phone', None) if self.instance else None)

        if self.instance is None:
            if not attrs.get('email') and not attrs.get('phone'):
                raise serializers.ValidationError(
                    {"non_field_errors": ["At least one contact method (Email or Phone Number) is required."]}
                )
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


class MemberProfileSerializer(serializers.ModelSerializer):
    """Public member profile resolved by profile_token."""

    class Meta:
        model = EmployeeCredential
        fields = [
            'name',
            'email',
            'phone',
            'company_name',
            'linkedin_url',
            'website_url',
        ]


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

class VisitorSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.name', read_only=True)
    session_title = serializers.CharField(source='session.title', read_only=True, default='')
    formatted_created_at = serializers.SerializerMethodField()

    class Meta:
        model = Visitor
        fields = [
            'id',
            'session',
            'session_title',
            'member',
            'member_name',
            'name',
            'email',
            'phone',
            'credential',
            'status',
            'scanned_at',
            'sent_at',
            'created_at',
            'formatted_created_at',
        ]
        read_only_fields = ['credential', 'scanned_at', 'sent_at', 'created_at']

    def get_formatted_created_at(self, obj):
        return obj.created_at.strftime("%m/%d/%Y, %I:%M %p")


class SubstituteSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.name', read_only=True)
    session_title = serializers.CharField(source='session.title', read_only=True, default='')
    formatted_created_at = serializers.SerializerMethodField()

    class Meta:
        model = Substitute
        fields = [
            'id',
            'session',
            'session_title',
            'member',
            'member_name',
            'name',
            'email',
            'phone',
            'credential',
            'status',
            'scanned_at',
            'sent_at',
            'created_at',
            'formatted_created_at',
        ]
        read_only_fields = ['credential', 'scanned_at', 'sent_at', 'created_at']

    def get_formatted_created_at(self, obj):
        return obj.created_at.strftime("%m/%d/%Y, %I:%M %p")


class VisitorSubstituteCreateSerializer(serializers.Serializer):
    """Create visitor or substitute"""
    type = serializers.ChoiceField(choices=['visitor', 'substitute'])
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class WalletChannelsSerializer(serializers.Serializer):
    """Optional delivery channels. Omitted means email only (existing clients)."""

    channels = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=False,
    )
    template_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_channels(self, value):
        normalized = []
        for item in value:
            name = str(item).strip().lower()
            if name not in ('email', 'whatsapp'):
                raise serializers.ValidationError(
                    'Each channel must be "email" or "whatsapp".'
                )
            if name not in normalized:
                normalized.append(name)
        return normalized

    def validate_template_id(self, value):
        if value is None:
            return None
        if not Template.objects.filter(pk=value).exists():
            raise serializers.ValidationError('Template not found.')
        return value


class VisitorSubstituteSendSerializer(WalletChannelsSerializer):
    type = serializers.ChoiceField(choices=['visitor', 'substitute'])


class EmployeeCredentialListSerializer(EmployeeCredentialSerializer):
    visitors = VisitorSerializer(source='issued_visitors', many=True, read_only=True)
    substitutes = SubstituteSerializer(source='issued_substitutes', many=True, read_only=True)

    class Meta(EmployeeCredentialSerializer.Meta):
        fields = EmployeeCredentialSerializer.Meta.fields + ['visitors', 'substitutes']


class PaymentHistorySerializer(serializers.ModelSerializer):
    """Serializer for payment history records."""
    employee_id = serializers.IntegerField(read_only=True)
    employee_name = serializers.CharField(source='employee.name', read_only=True)
    cycle_display = serializers.SerializerMethodField()

    class Meta:
        model = PaymentHistory
        fields = [
            'id',
            'employee',
            'employee_id',
            'employee_name',
            'cycle_start',
            'cycle_end',
            'cycle_display',
            'paid_at',
        ]
        read_only_fields = [
            'paid_at',
            'employee_id',
            'employee_name',
            'cycle_display',
        ]

    def get_cycle_display(self, obj):
        return format_cycle_display(obj.cycle_start, obj.cycle_end)


class PaymentReportSerializer(serializers.Serializer):
    """
    Serializer for payment report for a chapter in a specific cycle.
    Shows breakdown of paid vs unpaid members for that cycle.
    """
    chapter = ChapterSerializer()
    cycle_display = serializers.CharField()
    cycle_start = serializers.DateTimeField()
    cycle_end = serializers.DateTimeField()
    total_count = serializers.IntegerField()
    paid_count = serializers.IntegerField()
    unpaid_count = serializers.IntegerField()
    paid = EmployeeSummarySerializer(many=True)
    unpaid = EmployeeSummarySerializer(many=True)


APPLE_TEMPLATE_KEYS = (
    'foregroundColor',
    'backgroundColor',
    'labelColor',
    'logoText',
    'icon',
    'strip',
)
GOOGLE_TEMPLATE_KEYS = (
    'backgroundColor',
    'cardTitle',
    'heroImage',
    'logo',
)
_URL_FIELDS = frozenset({'icon', 'strip', 'heroImage', 'logo'})


def _validate_platform_section(value, required_keys, section_name):
    """Require a complete platform object with exactly the expected non-empty string fields."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise serializers.ValidationError(
            f'{section_name} must be an object or null.'
        )

    expected = set(required_keys)
    actual = set(value.keys())
    if actual != expected:
        raise serializers.ValidationError(
            f'All {section_name} fields are required; partial values are not allowed.'
        )

    cleaned = {}
    for key in required_keys:
        field_value = value[key]
        if not isinstance(field_value, str) or not field_value.strip():
            raise serializers.ValidationError(
                f'All {section_name} fields are required; partial values are not allowed.'
            )
        field_value = field_value.strip()
        if key in _URL_FIELDS:
            url_field = serializers.URLField()
            try:
                field_value = url_field.run_validation(field_value)
            except serializers.ValidationError:
                raise serializers.ValidationError(
                    {key: 'Must be a valid URL.'}
                )
        cleaned[key] = field_value
    return cleaned


class TemplateListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = ['id', 'name', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = ['id', 'name', 'apple', 'google', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def validate_apple(self, value):
        return _validate_platform_section(value, APPLE_TEMPLATE_KEYS, 'apple')

    def validate_google(self, value):
        return _validate_platform_section(value, GOOGLE_TEMPLATE_KEYS, 'google')

    def validate(self, attrs):
        apple = attrs.get('apple', serializers.empty)
        google = attrs.get('google', serializers.empty)

        if self.instance is not None:
            if apple is serializers.empty:
                apple = self.instance.apple
            if google is serializers.empty:
                google = self.instance.google
        else:
            if apple is serializers.empty:
                apple = None
            if google is serializers.empty:
                google = None

        if apple is None and google is None:
            raise serializers.ValidationError(
                'At least one full platform section (apple or google) is required.'
            )
        return attrs
