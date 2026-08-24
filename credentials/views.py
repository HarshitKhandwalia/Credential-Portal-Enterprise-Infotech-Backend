from django.shortcuts import render

# Create your views here.
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import EmployeeCredential
from .serializers import EmployeeCredentialSerializer
class EmployeeCredentialListCreateView(generics.ListCreateAPIView):
    name="Credentials list"
    queryset = EmployeeCredential.objects.all().order_by('-created_at')
    serializer_class = EmployeeCredentialSerializer


@api_view(['POST'])
def send_credential_invite(request, pk):
    try:
        employee = EmployeeCredential.objects.get(pk=pk)
    except EmployeeCredential.DoesNotExist:
        return Response({'error': 'Employee credential not found'}, status=status.HTTP_404_NOT_FOUND)

    email = request.data.get('email', employee.email)
    phone = request.data.get('phone', employee.phone)

    employee.email = email
    employee.phone = phone
    employee.status = 'invite_sent'
    employee.save()

    serializer = EmployeeCredentialSerializer(employee)
    return Response(serializer.data, status=status.HTTP_200_OK)
