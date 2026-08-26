from django.shortcuts import render
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import EmployeeCredential, ScanLog
from .serializers import EmployeeCredentialSerializer, ScanResponseSerializer, ScanLogSerializer

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

@api_view(['POST'])
def scan_qr(request):
    """
    Scan a QR code (contains the 8-digit code)
    Input: {"qr_code": "84920156", "device_id": "gate-1"}
    Returns: employee details + status (SUCCESS/DUPLICATE/NOT_FOUND)
    """
    qr_code = request.data.get('qr_code', '').strip()
    device_id = request.data.get('device_id', None)
    
    # Validate 8-digit format
    if not qr_code or not qr_code.isdigit() or len(qr_code) != 8:
        return Response(
            {'status': 'INVALID', 'message': 'QR code must be 8 digits'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        employee = EmployeeCredential.objects.get(qr_code=qr_code)
    except EmployeeCredential.DoesNotExist:
        # Log NOT_FOUND attempt
        ScanLog.objects.create(
            qr_code=qr_code,
            status='NOT_FOUND',
            device_id=device_id
        )
        return Response({
            'status': 'NOT_FOUND',
            'message': 'No employee found with this QR code',
            'employee': None
        }, status=status.HTTP_200_OK)
    
    # Check if already scanned
    if employee.is_attended:
        ScanLog.objects.create(
            employee=employee,
            qr_code=qr_code,
            status='DUPLICATE',
            device_id=device_id
        )
        return Response({
            'status': 'DUPLICATE',
            'message': 'This employee has already scanned',
            'employee': EmployeeCredentialSerializer(employee).data
        }, status=status.HTTP_200_OK)
    
    # Fresh scan - mark as attended
    employee.is_attended = True
    employee.attended_at = timezone.now()
    employee.save()
    
    # Log successful scan
    ScanLog.objects.create(
        employee=employee,
        qr_code=qr_code,
        status='SUCCESS',
        device_id=device_id
    )
    
    return Response({
        'status': 'SUCCESS',
        'message': 'Attendance marked successfully',
        'employee': EmployeeCredentialSerializer(employee).data
    }, status=status.HTTP_200_OK)
