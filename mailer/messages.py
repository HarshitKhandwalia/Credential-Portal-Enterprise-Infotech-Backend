from pathlib import Path

from django.conf import settings

from .client import send_email

TEMPLATES_DIR = Path(__file__).resolve().parent / 'templates'

WALLET_LINKS_SUBJECT = "Your credential invite - {{ name | default: 'there' }}"


def _load_template(filename):
    return (TEMPLATES_DIR / filename).read_text(encoding='utf-8')


def _build_wallet_links_html():
    return (
        _load_template('wallet_links.html')
        .replace('__APPLE_BUTTON_PNG_URL__', settings.APPLE_WALLET_BUTTON_PNG_URL)
        .replace('__GOOGLE_BUTTON_PNG_URL__', settings.GOOGLE_WALLET_BUTTON_PNG_URL)
    )


def send_wallet_links_email(*, to_email, name, apple_wallet_url, google_wallet_url):
    """Send the wallet-links invite email (Twilio variable template)."""
    return send_email(
        to_address=to_email,
        subject=WALLET_LINKS_SUBJECT,
        html=_build_wallet_links_html(),
        text=_load_template('wallet_links.txt'),
        variables={
            'name': name,
            'apple_wallet_url': apple_wallet_url,
            'google_wallet_url': google_wallet_url,
        },
    )
