from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail

REQUIRED_EMAIL_SETTINGS = (
    'EMAIL_HOST_USER',
    'EMAIL_HOST_PASSWORD',
    'DEFAULT_FROM_EMAIL',
)


def _validate_email_settings():
    missing_settings = [
        setting_name
        for setting_name in REQUIRED_EMAIL_SETTINGS
        if not getattr(settings, setting_name, None)
    ]
    if missing_settings:
        raise ImproperlyConfigured(
            'SMTP is not configured. Set the following environment variables: '
            + ', '.join(missing_settings)
        )


def send_wallet_links_email(employee, wallet_urls):
    _validate_email_settings()

    subject = f'Your credential invite - {employee.name}'
    message_lines = [
        f'Hello {employee.name},',
        '',
        'Choose how you would like to add your digital pass:',
        '',
        f'Apple Wallet: {wallet_urls["apple"]}',
        f'Google Wallet: {wallet_urls["google"]}',
        '',
        'Open the link for your device, then tap the wallet button to add your pass.',
        '',
        f'Credential: {employee.credential}',
        f'Membership ID: {employee.membership_id}',
    ]

    send_mail(
        subject=subject,
        message='\n'.join(message_lines),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[employee.email],
        fail_silently=False,
    )
