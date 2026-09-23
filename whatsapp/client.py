import re

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class WhatsAppError(RuntimeError):
    """Raised when the WhatsApp send API rejects or fails a send."""


def digits_only_phone(phone):
    """Keep digits only so +91 96436-87229 becomes 919643687229."""
    return re.sub(r'\D', '', phone or '')


def _validate_settings():
    missing = [
        name
        for name in ('WHATSAPP_SEND_URL', 'WHATSAPP_INSTANCE_ID')
        if not getattr(settings, name, None)
    ]
    if missing:
        raise ImproperlyConfigured(
            'WhatsApp is not configured. Set the following environment '
            'variables: ' + ', '.join(missing)
        )


def send_wallet_links_whatsapp(*, phone, name, apple_wallet_url, google_wallet_url):
    """Send wallet links as a WhatsApp text message."""
    _validate_settings()

    to = digits_only_phone(phone)
    if not to:
        raise WhatsAppError('Phone number is required to send a WhatsApp message.')

    message = settings.WHATSAPP_WALLET_MESSAGE.format(
        name=(name or '').strip() or 'there',
        apple_wallet_url=apple_wallet_url,
        google_wallet_url=google_wallet_url,
    )

    response = requests.post(
        settings.WHATSAPP_SEND_URL,
        json={
            'instanceId': settings.WHATSAPP_INSTANCE_ID,
            'to': to,
            'response_msg': message,
            'options': {'messageType': 'text'},
        },
        timeout=settings.WHATSAPP_TIMEOUT_SECONDS,
    )

    if not response.ok:
        raise WhatsAppError(
            f'WhatsApp send failed ({response.status_code}): {response.text}'
        )

    if not response.content:
        return None
    return response.json()
