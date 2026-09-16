from django.db import models

from .utils import generate_unique_credential


class Chapter(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Session(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='sessions')
    title = models.CharField(max_length=255, blank=True, default='')
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')

    class Meta:
        ordering = ['-starts_at']

    def __str__(self):
        label = self.title or f'Session {self.pk}'
        return f"{self.chapter.name} - {label}"


class EmployeeCredential(models.Model):
    STATUS_CHOICES = [
        ('not_invited', 'Not Invited'),
        ('invite_sent', 'Invite Sent'),
    ]

    PRIMARY_CREDENTIAL_CHOICES = [
        ('QR', 'QR'),
        ('NFC', 'NFC'),
    ]

    SECONDARY_CREDENTIAL_CHOICES = [
        ('Email', 'Email'),
        ('SMS', 'SMS'),
    ]

    name = models.CharField(max_length=255)
    membership_id = models.CharField(max_length=100, unique=True)
    credential = models.CharField(max_length=6, unique=True, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_invited')
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    primary_credential = models.CharField(max_length=50, choices=PRIMARY_CREDENTIAL_CHOICES, default='QR')
    secondary_credential = models.CharField(max_length=50, choices=SECONDARY_CREDENTIAL_CHOICES, default='Email')
    created_at = models.DateTimeField(auto_now_add=True)

    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
    )

    is_attended = models.BooleanField(default=False)
    attended_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.credential:
            self.credential = generate_unique_credential()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.credential}"


class SessionAttendance(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='attendances')
    employee = models.ForeignKey(
        EmployeeCredential,
        on_delete=models.CASCADE,
        related_name='session_attendances',
    )
    scanned_at = models.DateTimeField(auto_now_add=True)
    device_id = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        ordering = ['-scanned_at']
        constraints = [
            models.UniqueConstraint(
                fields=['session', 'employee'],
                name='unique_session_employee_attendance',
            ),
        ]

    def __str__(self):
        return f"{self.employee} @ {self.session_id}"


class ScanLog(models.Model):
    STATUS_CHOICES = [
        ('SUCCESS', 'Success'),
        ('DUPLICATE', 'Duplicate'),
        ('NOT_FOUND', 'Not Found'),
        ('WRONG_CHAPTER', 'Wrong Chapter'),
        ('INVALID', 'Invalid'),
    ]

    employee = models.ForeignKey(
        EmployeeCredential,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    session = models.ForeignKey(
        Session,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scan_logs',
    )
    credential = models.CharField(max_length=6)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    device_id = models.CharField(max_length=100, null=True, blank=True)
    scanned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scanned_at']

    def __str__(self):
        return f"{self.credential} - {self.status}"
class Visitor(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('scanned', 'Scanned'),
        ('cancelled', 'Cancelled'),
    ]

    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='visitors')
    member = models.ForeignKey(
        EmployeeCredential,
        on_delete=models.CASCADE,
        related_name='issued_visitors',
    )
    
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    credential = models.CharField(max_length=6, unique=True, editable=False)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    scanned_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['session', 'member', 'name'],
                name='unique_visitor_per_session_member',
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.credential:
            self.credential = generate_unique_credential()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Visitor: {self.name} ({self.member.name})"


class Substitute(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('scanned', 'Scanned'),
        ('cancelled', 'Cancelled'),
    ]

    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='substitutes')
    member = models.ForeignKey(
        EmployeeCredential,
        on_delete=models.CASCADE,
        related_name='issued_substitutes',
    )
    
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    credential = models.CharField(max_length=6, unique=True, editable=False)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    scanned_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['session', 'member', 'name'],
                name='unique_substitute_per_session_member',
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.credential:
            self.credential = generate_unique_credential()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Substitute: {self.name} ({self.member.name})"