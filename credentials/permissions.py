from rest_framework.permissions import BasePermission

from .models import StaffProfile


def get_staff_profile(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    try:
        return user.staff_profile
    except StaffProfile.DoesNotExist:
        return None


def is_superadmin(user):
    profile = get_staff_profile(user)
    return bool(
        profile
        and user.is_active
        and profile.role == StaffProfile.ROLE_SUPERADMIN
    )


def is_chapter_admin(user):
    profile = get_staff_profile(user)
    return bool(
        profile
        and user.is_active
        and profile.role == StaffProfile.ROLE_CHAPTER_ADMIN
        and profile.chapter_id
    )


class IsActiveStaff(BasePermission):
    message = 'You do not have permission to perform this action.'

    def has_permission(self, request, view):
        profile = get_staff_profile(request.user)
        return bool(profile and request.user.is_active)


class IsSuperadmin(BasePermission):
    message = 'You do not have permission to perform this action.'

    def has_permission(self, request, view):
        return is_superadmin(request.user)


def scope_by_chapter(queryset, user, chapter_lookup='chapter_id'):
    profile = get_staff_profile(user)
    if profile is None or not user.is_active:
        return queryset.none()
    if profile.role == StaffProfile.ROLE_SUPERADMIN:
        return queryset
    if not profile.chapter_id:
        return queryset.none()
    return queryset.filter(**{chapter_lookup: profile.chapter_id})


def scope_chapters(queryset, user):
    return scope_by_chapter(queryset, user, chapter_lookup='pk')
