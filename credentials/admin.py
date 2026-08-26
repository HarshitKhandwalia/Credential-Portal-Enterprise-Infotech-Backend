from django.contrib import admin
from .models import EmployeeCredential, ScanLog

@admin.register(EmployeeCredential)
class EmployeeCredentialAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'qr_code', 'is_attended', 'created_at']
    search_fields = ['name', 'email', 'qr_code']
    readonly_fields = ['created_at']

@admin.register(ScanLog)
class ScanLogAdmin(admin.ModelAdmin):
    list_display = ['qr_code', 'status', 'device_id', 'scanned_at']
    search_fields = ['qr_code']
    readonly_fields = ['scanned_at']