import requests
from django.conf import settings

PASS_LINK_KEYS = ('pass_url', 'url', 'link', 'save_url', 'download_url')


def _build_google_payload(employee):
    return {
        'name': employee.name,
        'credential': employee.credential,
        'membership_id': employee.membership_id,
    }


def _build_apple_payload(employee):
    return {
        'foregroundColor': 'rgb(255,255,255)',
        'backgroundColor': 'rgb(196,36,42)',
        'labelColor': 'rgb(255,255,255)',
        'userName': employee.name,
        'membershipId': employee.membership_id,
        'barcodeMessage': employee.credential,
        'serialNumber': employee.membership_id,
    }


def _request_json_pass_service(url, payload):
    try:
        service_response = requests.post(
            url,
            json=payload,
            timeout=settings.PASS_SERVICE_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        return {
            'success': False,
            'status_code': None,
            'error': str(exc),
        }

    try:
        response_data = service_response.json()
    except ValueError:
        return {
            'success': False,
            'status_code': service_response.status_code,
            'error': 'Pass service returned an invalid JSON response.',
        }

    return {
        'success': service_response.ok,
        'status_code': service_response.status_code,
        'data': response_data,
    }


def extract_pass_link(service_result):
    if not service_result.get('success'):
        return None

    data = service_result.get('data')
    if isinstance(data, str) and data.startswith('http'):
        return data

    if not isinstance(data, dict):
        return None

    for key in PASS_LINK_KEYS:
        value = data.get(key)
        if isinstance(value, str) and value.startswith('http'):
            return value

    return None


def generate_google_pass(employee):
    return _request_json_pass_service(
        f"{settings.GOOGLE_PASS_SERVICE_URL.rstrip('/')}/passes/qr",
        _build_google_payload(employee),
    )


def generate_apple_pass(employee):
    url = f"{settings.APPLE_PASS_SERVICE_URL.rstrip('/')}/generate_apple_pass"
    payload = _build_apple_payload(employee)

    try:
        service_response = requests.post(
            url,
            json=payload,
            timeout=settings.PASS_SERVICE_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        return {
            'success': False,
            'status_code': None,
            'error': str(exc),
        }

    if not service_response.ok:
        error_message = 'Apple pass service returned an error.'
        content_type = service_response.headers.get('Content-Type', '')
        if 'json' in content_type:
            try:
                error_data = service_response.json()
                error_message = error_data.get('error', error_message)
            except ValueError:
                pass

        return {
            'success': False,
            'status_code': service_response.status_code,
            'error': error_message,
        }

    return {
        'success': True,
        'status_code': service_response.status_code,
        'content': service_response.content,
        'content_type': service_response.headers.get(
            'Content-Type',
            'application/vnd.apple.pkpass',
        ),
    }
