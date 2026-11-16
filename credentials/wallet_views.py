from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import EmployeeCredential, Substitute, Template, Visitor
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


def _resolve_wallet_context(token, platform):
    """
    Resolve pass subject + optional template from a wallet link token.
    Returns (subject, template) or a WalletTokenError.
    """
    try:
        subject_kind, subject_id, template_id = verify_wallet_token(token, platform)
    except WalletTokenError as exc:
        return exc

    if subject_kind == PASS_KIND_EMPLOYEE:
        try:
            employee = EmployeeCredential.objects.get(pk=subject_id)
        except EmployeeCredential.DoesNotExist:
            return WalletTokenError('invalid', 'Credential not found.')
        subject = pass_subject_from_employee(employee)
    elif subject_kind == PASS_KIND_VISITOR:
        try:
            visitor = Visitor.objects.select_related('member').get(pk=subject_id)
        except Visitor.DoesNotExist:
            return WalletTokenError('invalid', 'Visitor not found.')
        subject = pass_subject_from_visitor(visitor)
    elif subject_kind == PASS_KIND_SUBSTITUTE:
        try:
            substitute = Substitute.objects.select_related('member').get(pk=subject_id)
        except Substitute.DoesNotExist:
            return WalletTokenError('invalid', 'Substitute not found.')
        subject = pass_subject_from_substitute(substitute)
    else:
        return WalletTokenError('invalid', 'This wallet link is invalid.')

    template = None
    if template_id is not None:
        template = Template.objects.filter(pk=template_id).first()

    return subject, template


@api_view(['GET'])
def wallet_apple_detail(request, token):
    resolved = _resolve_wallet_context(token, 'apple')
    if isinstance(resolved, WalletTokenError):
        return _wallet_token_error_response(resolved)

    subject, _template = resolved
    return Response({'name': subject.name})


@api_view(['POST'])
def wallet_apple_generate(request, token):
    resolved = _resolve_wallet_context(token, 'apple')
    if isinstance(resolved, WalletTokenError):
        return _wallet_token_error_response(resolved)

    subject, template = resolved
    result = generate_apple_pass(subject, template=template)
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
    resolved = _resolve_wallet_context(token, 'google')
    if isinstance(resolved, WalletTokenError):
        return _wallet_token_error_response(resolved)

    subject, _template = resolved
    return Response({'name': subject.name})


@api_view(['POST'])
def wallet_google_generate(request, token):
    resolved = _resolve_wallet_context(token, 'google')
    if isinstance(resolved, WalletTokenError):
        return _wallet_token_error_response(resolved)

    subject, template = resolved
    result = generate_google_pass(subject, template=template)
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
