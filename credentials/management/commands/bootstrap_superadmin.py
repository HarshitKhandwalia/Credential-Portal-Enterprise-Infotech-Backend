from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from credentials.models import StaffProfile


class Command(BaseCommand):
    help = (
        'Create the first superadmin from SUPERADMIN_EMAIL and SUPERADMIN_PASSWORD. '
        'If that email already exists, the password is left unchanged.'
    )

    def handle(self, *args, **options):
        email = (settings.SUPERADMIN_EMAIL or '').strip().lower()
        password = settings.SUPERADMIN_PASSWORD or ''
        if not email or not password:
            raise CommandError('SUPERADMIN_EMAIL and SUPERADMIN_PASSWORD are required.')

        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        if user is not None:
            profile = StaffProfile.objects.filter(user=user).first()
            if profile is None or profile.role != StaffProfile.ROLE_SUPERADMIN:
                raise CommandError(
                    f'{email} already exists and is not a superadmin. '
                    'Choose a different SUPERADMIN_EMAIL.'
                )
            self.stdout.write(self.style.WARNING(f'Superadmin {email} already exists.'))
            return

        user = User(
            username=email,
            email=email,
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )
        user.set_password(password)
        user.save()
        StaffProfile.objects.create(
            user=user,
            name='Superadmin',
            role=StaffProfile.ROLE_SUPERADMIN,
            chapter=None,
        )
        self.stdout.write(self.style.SUCCESS(f'Created superadmin {email}.'))
