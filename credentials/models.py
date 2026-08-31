from django.db import models

# Create your models here.

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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_invited')
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    primary_credential = models.CharField(max_length=50, choices=PRIMARY_CREDENTIAL_CHOICES, default='QR')
    secondary_credential = models.CharField(max_length=50, choices=SECONDARY_CREDENTIAL_CHOICES, default='Email')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.secondary_credential}"