from django.contrib import admin
from .models import EmployeeCredential, ScanLog

@admin.register(EmployeeCredential)
class EmployeeCredentialAdmin(admin.ModelAdmin):
    list_display = ['name', 'membership_id', 'credential', 'email', 'status', 'is_attended', 'created_at']
    search_fields = ['name', 'membership_id', 'credential', 'email']
    readonly_fields = ['credential', 'created_at']

@admin.register(ScanLog)
class ScanLogAdmin(admin.ModelAdmin):
    list_display = ['credential', 'employee', 'status', 'device_id', 'scanned_at']
    search_fields = ['credential']
    readonly_fields = ['scanned_at']