from dataclasses import dataclass

import requests
from django.conf import settings

PASS_LINK_KEYS = ('pass_url', 'url', 'link', 'save_url', 'download_url')

CARD_TITLE_MEMBER = 'BNI Membership Card'
CARD_TITLE_VISITOR = 'BNI Visitor Card'
CARD_TITLE_SUBSTITUTE = 'BNI Substitute Card'


@dataclass(frozen=True)
class PassSubject:
    name: str
    credential: str
    membership_id: str
    card_title: str


def pass_subject_from_employee(employee):
    return PassSubject(
        name=employee.name,
        credential=employee.credential,
        membership_id=employee.membership_id,
        card_title=CARD_TITLE_MEMBER,
    )


def pass_subject_from_visitor(visitor):
    return PassSubject(
        name=visitor.name,
        credential=visitor.credential,
        membership_id=f'{visitor.member.membership_id}-V-{visitor.pk}',
        card_title=CARD_TITLE_VISITOR,
    )


def pass_subject_from_substitute(substitute):
    return PassSubject(
        name=substitute.name,
        credential=substitute.credential,
        membership_id=f'{substitute.member.membership_id}-S-{substitute.pk}',
        card_title=CARD_TITLE_SUBSTITUTE,
    )


def _build_google_payload(subject):
    return {
        'name': subject.name,
        'credential': subject.credential,
        'membership_id': subject.membership_id,
        'card_title': subject.card_title,
    }


def _build_apple_payload(subject):
    return {
        'foregroundColor': 'rgb(255,255,255)',
        'backgroundColor': 'rgb(196,36,42)',
        'labelColor': 'rgb(255,255,255)',
        'userName': subject.name,
        'membershipId': subject.membership_id,
        'barcodeMessage': subject.credential,
        'serialNumber': subject.membership_id,
        'logoText': subject.card_title,
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


def generate_google_pass(subject):
    return _request_json_pass_service(
        f"{settings.GOOGLE_PASS_SERVICE_URL.rstrip('/')}/passes/qr",
        _build_google_payload(subject),
    )


def generate_apple_pass(subject):
    url = f"{settings.APPLE_PASS_SERVICE_URL.rstrip('/')}/generate_apple_pass"
    payload = _build_apple_payload(subject)

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
