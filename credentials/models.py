from django.db import models

class EmployeeCredential(models.Model):
    STATUS_CHOICES = [
        ('not_invited', 'Not Invited'),
        ('invite_sent', 'Invite Sent'),
    ]
    PRIMARY_CREDENTIAL_CHOICES = [
        ('QR / NFC', 'QR / NFC'),
    ]
    SECONDARY_CREDENTIAL_CHOICES = [
        ('Email', 'Email'),
        ('SMS', 'SMS'),
    ]
    
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_invited')
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    primary_credential = models.CharField(max_length=50, choices=PRIMARY_CREDENTIAL_CHOICES, default='QR / NFC')
    secondary_credential = models.CharField(max_length=50, choices=SECONDARY_CREDENTIAL_CHOICES, default='Email')
    created_at = models.DateTimeField(auto_now_add=True)
    

    qr_code = models.CharField(max_length=8, unique=True, null=True, blank=True)
    is_attended = models.BooleanField(default=False)   
    attended_at = models.DateTimeField(null=True, blank=True)

    
    def __str__(self):
        return f"{self.name} - {self.qr_code if self.qr_code else 'No QR'}"



class ScanLog(models.Model):
    STATUS_CHOICES = [
        ('SUCCESS', 'Success'),
        ('DUPLICATE', 'Duplicate'),
        ('NOT_FOUND', 'Not Found'),
    ]
    
    employee = models.ForeignKey(EmployeeCredential, on_delete=models.CASCADE, null=True, blank=True)
    qr_code = models.CharField(max_length=8)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    device_id = models.CharField(max_length=100, null=True, blank=True)
    scanned_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.qr_code} - {self.status}"
