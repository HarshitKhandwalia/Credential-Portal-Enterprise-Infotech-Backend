import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

TWILIO_EMAILS_URL = 'https://comms.twilio.com/v1/Emails'

REQUIRED_SETTINGS = (
    'TWILIO_API_KEY',
    'TWILIO_CLIENT_SECRET',
    'TWILIO_FROM_EMAIL',
    'TWILIO_FROM_NAME',
)


class TwilioEmailError(RuntimeError):
    """Raised when the Twilio Emails API rejects or fails a send."""


def _validate_settings():
    missing = [
        name
        for name in REQUIRED_SETTINGS
        if not getattr(settings, name, None)
    ]
    if missing:
        raise ImproperlyConfigured(
            'Twilio email is not configured. Set the following environment '
            'variables: ' + ', '.join(missing)
        )


def send_email(*, to_address, subject, html, text=None, variables=None):
    """
    Send a single personalized email via Twilio Emails API.

    ``subject``, ``html``, and ``text`` may contain Twilio template
    placeholders such as ``{{ name }}``. Values are supplied in ``variables``.
    """
    _validate_settings()

    payload = {
        'from': {
            'address': settings.TWILIO_FROM_EMAIL,
            'name': settings.TWILIO_FROM_NAME,
        },
        'to': [
            {
                'address': to_address,
                'variables': variables or {},
            }
        ],
        'content': {
            'subject': subject,
            'html': html,
            'text': text if text is not None else '',
        },
    }

    response = requests.post(
        TWILIO_EMAILS_URL,
        json=payload,
        auth=(settings.TWILIO_API_KEY, settings.TWILIO_CLIENT_SECRET),
        timeout=30,
    )

    if not response.ok:
        raise TwilioEmailError(
            f'Twilio email failed ({response.status_code}): {response.text}'
        )

    if not response.content:
        return None
    return response.json()
