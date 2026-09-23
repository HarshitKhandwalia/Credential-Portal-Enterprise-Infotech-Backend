from mailer import send_wallet_links_email
from whatsapp import send_wallet_links_whatsapp

CHANNEL_EMAIL = 'email'
CHANNEL_WHATSAPP = 'whatsapp'


def deliver_wallet_links(*, name, email, phone, wallet_urls, channels):
    """
    Send wallet links on each requested channel.

    Returns a dict with email_sent / whatsapp_sent for the channels that were
    requested, plus an errors map for any channel that did not send.
    """
    result = {'wallet_urls': wallet_urls}
    errors = {}

    if CHANNEL_EMAIL in channels:
        if not email:
            result['email_sent'] = False
            errors['email'] = 'Email is required to send wallet links.'
        else:
            try:
                send_wallet_links_email(
                    to_email=email,
                    name=name,
                    apple_wallet_url=wallet_urls['apple'],
                    google_wallet_url=wallet_urls['google'],
                )
                result['email_sent'] = True
            except Exception as exc:
                result['email_sent'] = False
                errors['email'] = f'Failed to send wallet email: {exc}'

    if CHANNEL_WHATSAPP in channels:
        if not phone:
            result['whatsapp_sent'] = False
            errors['whatsapp'] = 'Phone number is required to send a WhatsApp message.'
        else:
            try:
                send_wallet_links_whatsapp(
                    phone=phone,
                    name=name,
                    apple_wallet_url=wallet_urls['apple'],
                    google_wallet_url=wallet_urls['google'],
                )
                result['whatsapp_sent'] = True
            except Exception as exc:
                result['whatsapp_sent'] = False
                errors['whatsapp'] = f'Failed to send WhatsApp message: {exc}'

    if errors:
        result['errors'] = errors
    return result
