from django.contrib import admin

from .models import Chapter, EmployeeCredential, ScanLog, Session, SessionAttendance


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    search_fields = ['name']
    list_filter = ['is_active']


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'chapter', 'starts_at', 'ends_at', 'status']
    search_fields = ['title', 'chapter__name']
    list_filter = ['status', 'chapter']


@admin.register(SessionAttendance)
class SessionAttendanceAdmin(admin.ModelAdmin):
    list_display = ['session', 'employee', 'scanned_at', 'device_id']
    search_fields = ['employee__name', 'employee__credential', 'session__title']
    readonly_fields = ['scanned_at']


@admin.register(EmployeeCredential)
class EmployeeCredentialAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'membership_id',
        'credential',
        'chapter',
        'email',
        'status',
        'is_attended',
        'created_at',
    ]
    search_fields = ['name', 'membership_id', 'credential', 'email']
    list_filter = ['chapter', 'status']
    readonly_fields = ['credential', 'created_at', 'attended_at']


@admin.register(ScanLog)
class ScanLogAdmin(admin.ModelAdmin):
    list_display = ['credential', 'employee', 'session', 'status', 'device_id', 'scanned_at']
    search_fields = ['credential']
    list_filter = ['status']
    readonly_fields = ['scanned_at']
