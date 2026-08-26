from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import EmployeeCredential
from .serializers import EmployeeCredentialSerializer


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = EmployeeCredential.objects.all().order_by('-created_at')
    serializer_class = EmployeeCredentialSerializer
def get_view_name(self):
        return "Credentials list"

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