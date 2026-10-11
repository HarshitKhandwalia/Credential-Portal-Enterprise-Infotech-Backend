from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Chapter, StaffProfile
from .permissions import IsActiveStaff, IsSuperadmin, get_staff_profile

User = get_user_model()

INVALID_LOGIN = {'detail': 'Invalid email or password.'}
ACCOUNT_DISABLED = {'detail': 'This account has been disabled. Please contact support.'}


def staff_payload(profile):
    chapter = profile.chapter
    return {
        'id': profile.pk,
        'name': profile.name,
        'email': profile.user.email,
        'role': profile.role,
        'is_active': profile.user.is_active,
        'chapter': chapter.pk if chapter else None,
        'chapter_name': chapter.name if chapter else None,
    }


def _normalize_email(value):
    return (value or '').strip().lower()


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        email = _normalize_email(request.data.get('email'))
        password = request.data.get('password') or ''
        user = User.objects.filter(email__iexact=email).first() if email else None
        profile = get_staff_profile(user) if user else None
        if user is None or profile is None or not user.check_password(password):
            return Response(INVALID_LOGIN, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            return Response(ACCOUNT_DISABLED, status=status.HTTP_403_FORBIDDEN)

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': staff_payload(profile),
            }
        )


class LogoutView(APIView):
    permission_classes = [IsActiveStaff]

    def post(self, request):
        raw = request.data.get('refresh')
        if not raw:
            return Response(
                {'refresh': ['This field is required.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(raw)
            token.blacklist()
        except TokenError:
            return Response(
                {'detail': 'Invalid refresh token.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsActiveStaff]

    def get(self, request):
        return Response(staff_payload(request.user.staff_profile))


class ChangePasswordView(APIView):
    permission_classes = [IsActiveStaff]

    def post(self, request):
        old_password = request.data.get('old_password') or ''
        new_password = request.data.get('new_password') or ''
        if not request.user.check_password(old_password):
            return Response(
                {'old_password': ['Password is incorrect.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_password(new_password, user=request.user)
        except DjangoValidationError as exc:
            return Response(
                {'new_password': list(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.set_password(new_password)
        request.user.save(update_fields=['password'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class StaffListCreateView(APIView):
    permission_classes = [IsSuperadmin]

    def get(self, request):
        profiles = (
            StaffProfile.objects.filter(role=StaffProfile.ROLE_CHAPTER_ADMIN)
            .select_related('user', 'chapter')
            .order_by('name')
        )
        return Response([staff_payload(profile) for profile in profiles])

    def post(self, request):
        name = (request.data.get('name') or '').strip()
        email = _normalize_email(request.data.get('email'))
        password = request.data.get('password') or ''
        chapter_id = request.data.get('chapter')
        errors = {}
        if not name:
            errors['name'] = ['This field is required.']
        if not email:
            errors['email'] = ['This field is required.']
        elif User.objects.filter(email__iexact=email).exists():
            errors['email'] = ['A user with this email already exists.']
        if not password:
            errors['password'] = ['This field is required.']
        chapter = None
        if not chapter_id:
            errors['chapter'] = ['This field is required.']
        else:
            chapter = Chapter.objects.filter(pk=chapter_id).first()
            if chapter is None:
                errors['chapter'] = ['Chapter not found.']
        if password and 'password' not in errors:
            try:
                validate_password(password)
            except DjangoValidationError as exc:
                errors['password'] = list(exc.messages)
        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        user = User(
            username=email,
            email=email,
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )
        user.set_password(password)
        user.save()
        profile = StaffProfile.objects.create(
            user=user,
            name=name,
            role=StaffProfile.ROLE_CHAPTER_ADMIN,
            chapter=chapter,
        )
        return Response(staff_payload(profile), status=status.HTTP_201_CREATED)


class StaffDetailView(APIView):
    permission_classes = [IsSuperadmin]

    def _get_profile(self, pk):
        return (
            StaffProfile.objects.filter(role=StaffProfile.ROLE_CHAPTER_ADMIN, pk=pk)
            .select_related('user', 'chapter')
            .first()
        )

    def patch(self, request, pk):
        profile = self._get_profile(pk)
        if profile is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        user = profile.user
        errors = {}
        update_user_fields = []

        if 'name' in request.data:
            name = (request.data.get('name') or '').strip()
            if not name:
                errors['name'] = ['This field may not be blank.']
            else:
                profile.name = name

        if 'chapter' in request.data:
            chapter = Chapter.objects.filter(pk=request.data.get('chapter')).first()
            if chapter is None:
                errors['chapter'] = ['Chapter not found.']
            else:
                profile.chapter = chapter

        if 'is_active' in request.data:
            is_active = request.data.get('is_active')
            if not isinstance(is_active, bool):
                errors['is_active'] = ['Must be true or false.']
            else:
                user.is_active = is_active
                update_user_fields.append('is_active')

        if 'password' in request.data:
            password = request.data.get('password') or ''
            try:
                validate_password(password, user=user)
            except DjangoValidationError as exc:
                errors['password'] = list(exc.messages)
            else:
                user.set_password(password)
                update_user_fields.append('password')

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        if update_user_fields:
            user.save(update_fields=update_user_fields)
        profile.save()
        profile.refresh_from_db()
        return Response(staff_payload(profile))
