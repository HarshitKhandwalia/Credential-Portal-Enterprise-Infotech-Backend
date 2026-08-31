import os

from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner

WALLET_SIGNER_SALT = 'wallet-pass-v1'
DEFAULT_FRONTEND_BASE_URL = 'http://localhost:5173'
DEFAULT_WALLET_TOKEN_EXPIRY_DAYS = 7


class WalletTokenError(Exception):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def _get_signer():
    return TimestampSigner(salt=WALLET_SIGNER_SALT)


def create_wallet_token(employee_id, platform):
    return _get_signer().sign_object(
        {
            'employee_id': employee_id,
            'platform': platform,
        },
    )


def _get_wallet_token_expiry_seconds():
    expiry_seconds = getattr(settings, 'WALLET_TOKEN_EXPIRY_SECONDS', None)
    if expiry_seconds:
        return expiry_seconds

    expiry_days = os.getenv('WALLET_TOKEN_EXPIRY_DAYS', str(DEFAULT_WALLET_TOKEN_EXPIRY_DAYS))
    return int(expiry_days) * 24 * 60 * 60


def _get_frontend_base_url():
    base_url = getattr(settings, 'FRONTEND_BASE_URL', None) or os.getenv(
        'FRONTEND_BASE_URL',
        DEFAULT_FRONTEND_BASE_URL,
    )
    return base_url.rstrip('/')


def verify_wallet_token(token, expected_platform):
    try:
        payload = _get_signer().unsign_object(
            token,
            max_age=_get_wallet_token_expiry_seconds(),
        )
    except SignatureExpired as exc:
        raise WalletTokenError('expired', 'This wallet link has expired.') from exc
    except BadSignature as exc:
        raise WalletTokenError('invalid', 'This wallet link is invalid.') from exc

    platform = payload.get('platform')
    employee_id = payload.get('employee_id')

    if platform != expected_platform:
        raise WalletTokenError(
            'invalid_platform',
            'This wallet link is not valid for the requested platform.',
        )

    if not employee_id:
        raise WalletTokenError('invalid', 'This wallet link is invalid.')

    return employee_id


def build_wallet_urls(employee):
    base_url = _get_frontend_base_url()
    apple_token = create_wallet_token(employee.pk, 'apple')
    google_token = create_wallet_token(employee.pk, 'google')

    return {
        'apple': f'{base_url}/wallet/apple/{apple_token}',
        'google': f'{base_url}/wallet/google/{google_token}',
    }
