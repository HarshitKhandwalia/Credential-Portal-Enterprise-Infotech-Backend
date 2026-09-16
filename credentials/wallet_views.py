from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import EmployeeCredential, Substitute, Visitor
from .pass_services import (
    extract_pass_link,
    generate_apple_pass,
    generate_google_pass,
    pass_subject_from_employee,
    pass_subject_from_substitute,
    pass_subject_from_visitor,
)
from .wallet_tokens import (
    PASS_KIND_EMPLOYEE,
    PASS_KIND_SUBSTITUTE,
    PASS_KIND_VISITOR,
    WalletTokenError,
    verify_wallet_token,
)


def _wallet_token_error_response(exc):
    status_code = status.HTTP_400_BAD_REQUEST
    if exc.code == 'expired':
        status_code = status.HTTP_410_GONE

    return Response({'error': str(exc)}, status=status_code)


def _get_pass_subject_from_wallet_token(token, platform):
    try:
        subject_kind, subject_id = verify_wallet_token(token, platform)
    except WalletTokenError as exc:
        return exc

    if subject_kind == PASS_KIND_EMPLOYEE:
        try:
            employee = EmployeeCredential.objects.get(pk=subject_id)
        except EmployeeCredential.DoesNotExist:
            return WalletTokenError('invalid', 'Credential not found.')
        return pass_subject_from_employee(employee)

    if subject_kind == PASS_KIND_VISITOR:
        try:
            visitor = Visitor.objects.select_related('member').get(pk=subject_id)
        except Visitor.DoesNotExist:
            return WalletTokenError('invalid', 'Visitor not found.')
        return pass_subject_from_visitor(visitor)

    if subject_kind == PASS_KIND_SUBSTITUTE:
        try:
            substitute = Substitute.objects.select_related('member').get(pk=subject_id)
        except Substitute.DoesNotExist:
            return WalletTokenError('invalid', 'Substitute not found.')
        return pass_subject_from_substitute(substitute)

    return WalletTokenError('invalid', 'This wallet link is invalid.')


@api_view(['GET'])
def wallet_apple_detail(request, token):
    subject = _get_pass_subject_from_wallet_token(token, 'apple')
    if isinstance(subject, WalletTokenError):
        return _wallet_token_error_response(subject)

    return Response({'name': subject.name})


@api_view(['POST'])
def wallet_apple_generate(request, token):
    subject = _get_pass_subject_from_wallet_token(token, 'apple')
    if isinstance(subject, WalletTokenError):
        return _wallet_token_error_response(subject)

    result = generate_apple_pass(subject)
    if not result.get('success'):
        return Response(
            {'error': result.get('error', 'Failed to generate Apple pass.')},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    response = HttpResponse(
        result['content'],
        content_type=result['content_type'],
    )
    response['Content-Disposition'] = 'attachment; filename="pass.pkpass"'
    return response


@api_view(['GET'])
def wallet_google_detail(request, token):
    subject = _get_pass_subject_from_wallet_token(token, 'google')
    if isinstance(subject, WalletTokenError):
        return _wallet_token_error_response(subject)

    return Response({'name': subject.name})


@api_view(['POST'])
def wallet_google_generate(request, token):
    subject = _get_pass_subject_from_wallet_token(token, 'google')
    if isinstance(subject, WalletTokenError):
        return _wallet_token_error_response(subject)

    result = generate_google_pass(subject)
    if not result.get('success'):
        return Response(
            {'error': result.get('error', 'Failed to generate Google pass.')},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    pass_url = extract_pass_link(result)
    if not pass_url:
        return Response(
            {'error': 'Google pass service did not return a valid URL.'},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    return Response({'url': pass_url})
