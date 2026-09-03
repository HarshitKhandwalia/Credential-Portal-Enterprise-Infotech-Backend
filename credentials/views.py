from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from mailer import send_wallet_links_email

from .models import EmployeeCredential
from .serializers import EmployeeCredentialSerializer
from .wallet_tokens import build_wallet_urls


@api_view(['GET'])
def health_check(request):
    return Response({'status': 'ok'})


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = EmployeeCredential.objects.all().order_by('-created_at')
    serializer_class = EmployeeCredentialSerializer


def get_view_name(self):
    return "Credentials list"


@api_view(['POST'])
def generate_QR_passes(request, pk):
    try:
        employee = EmployeeCredential.objects.get(pk=pk)
    except EmployeeCredential.DoesNotExist:
        return Response(
            {'error': 'Credential not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not employee.email:
        return Response(
            {'error': 'Email is required to send wallet links.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    wallet_urls = build_wallet_urls(employee)

    try:
        send_wallet_links_email(
            to_email=employee.email,
            name=employee.name,
            apple_wallet_url=wallet_urls['apple'],
            google_wallet_url=wallet_urls['google'],
        )
    except Exception as exc:
        return Response(
            {
                'error': f'Failed to send wallet email: {exc}',
                'employee_id': employee.pk,
                'wallet_urls': wallet_urls,
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )

    return Response(
        {
            'employee_id': employee.pk,
            'email_sent': True,
            'wallet_urls': wallet_urls,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
def send_credential_invite(request, pk):
    try:
        employee = EmployeeCredential.objects.get(pk=pk)
    except EmployeeCredential.DoesNotExist:
        return Response({'error': 'Credential not found'}, status=status.HTTP_404_NOT_FOUND)

    email = request.data.get('email', employee.email)
    phone = request.data.get('phone', employee.phone)

    employee.email = email
    employee.phone = phone
    employee.status = 'invite_sent'
    employee.save()

    serializer = EmployeeCredentialSerializer(employee)
    return Response(serializer.data, status=status.HTTP_200_OK)
