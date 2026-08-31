from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import EmployeeCredential
from .pass_services import extract_pass_link, generate_apple_pass, generate_google_pass
from .wallet_tokens import WalletTokenError, verify_wallet_token


def _wallet_token_error_response(exc):
    status_code = status.HTTP_400_BAD_REQUEST
    if exc.code == 'expired':
        status_code = status.HTTP_410_GONE

    return Response({'error': str(exc)}, status=status_code)


def _get_employee_from_wallet_token(token, platform):
    try:
        employee_id = verify_wallet_token(token, platform)
        return EmployeeCredential.objects.get(pk=employee_id)
    except WalletTokenError as exc:
        return exc
    except EmployeeCredential.DoesNotExist:
        return WalletTokenError('invalid', 'Credential not found.')


@api_view(['GET'])
def wallet_apple_detail(request, token):
    employee = _get_employee_from_wallet_token(token, 'apple')
    if isinstance(employee, WalletTokenError):
        return _wallet_token_error_response(employee)

    return Response({'name': employee.name})


@api_view(['POST'])
def wallet_apple_generate(request, token):
    employee = _get_employee_from_wallet_token(token, 'apple')
    if isinstance(employee, WalletTokenError):
        return _wallet_token_error_response(employee)

    result = generate_apple_pass(employee)
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
    employee = _get_employee_from_wallet_token(token, 'google')
    if isinstance(employee, WalletTokenError):
        return _wallet_token_error_response(employee)

    return Response({'name': employee.name})


@api_view(['POST'])
def wallet_google_generate(request, token):
    employee = _get_employee_from_wallet_token(token, 'google')
    if isinstance(employee, WalletTokenError):
        return _wallet_token_error_response(employee)

    result = generate_google_pass(employee)
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
