from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from mailer import send_wallet_links_email

from .models import Chapter, EmployeeCredential, ScanLog, Session, SessionAttendance
from .serializers import (
    ChapterSerializer,
    EmployeeCredentialSerializer,
    EmployeeSummarySerializer,
    SessionSerializer,
)
from .wallet_tokens import build_wallet_urls


@api_view(['GET'])
def health_check(request):
    return Response({'status': 'ok'})


class ChapterViewSet(viewsets.ModelViewSet):
    serializer_class = ChapterSerializer

    def get_queryset(self):
        qs = Chapter.objects.all().order_by('name')
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            value = is_active.strip().lower()
            if value in ('true', '1', 'yes'):
                qs = qs.filter(is_active=True)
            elif value in ('false', '0', 'no'):
                qs = qs.filter(is_active=False)
        return qs

    @action(detail=True, methods=['get', 'post'], url_path='sessions')
    def sessions(self, request, pk=None):
        chapter = self.get_object()
        if request.method == 'GET':
            sessions = chapter.sessions.all().order_by('-starts_at')
            return Response(SessionSerializer(sessions, many=True).data)

        serializer = SessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = serializer.save(chapter=chapter)
        return Response(SessionSerializer(session).data, status=status.HTTP_201_CREATED)


class SessionViewSet(viewsets.ModelViewSet):
    queryset = Session.objects.select_related('chapter').all().order_by('-starts_at')
    serializer_class = SessionSerializer
    http_method_names = ['get', 'patch', 'put', 'delete', 'head', 'options']

    @action(detail=True, methods=['get'], url_path='report')
    def report(self, request, pk=None):
        session = self.get_object()
        members = list(
            EmployeeCredential.objects.filter(chapter_id=session.chapter_id).order_by('name')
        )
        attended_qs = (
            SessionAttendance.objects.filter(session=session)
            .select_related('employee')
            .order_by('scanned_at')
        )
        attended_employees = [row.employee for row in attended_qs]
        attended_ids = {emp.pk for emp in attended_employees}
        absent_employees = [emp for emp in members if emp.pk not in attended_ids]

        return Response(
            {
                'session': SessionSerializer(session).data,
                'expected_count': len(members),
                'attended_count': len(attended_employees),
                'absent_count': len(absent_employees),
                'attended': EmployeeSummarySerializer(attended_employees, many=True).data,
                'absent': EmployeeSummarySerializer(absent_employees, many=True).data,
            }
        )


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = EmployeeCredential.objects.select_related('chapter').all().order_by('-created_at')
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


@api_view(['POST'])
def scan_credential(request):
    """
    Scan a 6-digit credential for a specific session.

    Input: {"credential": "849201", "session_id": 12, "device_id": "gate-1"}
    Returns: employee details + status
    """
    credential = str(request.data.get('credential', '')).strip()
    device_id = request.data.get('device_id', None)
    session_id = request.data.get('session_id', None)

    if not credential or not credential.isdigit() or len(credential) != 6:
        return Response(
            {
                'status': 'INVALID',
                'message': 'Credential must be 6 digits',
                'employee': None,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if session_id is None:
        return Response(
            {
                'status': 'INVALID',
                'message': 'session_id is required',
                'employee': None,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        session = Session.objects.select_related('chapter').get(pk=session_id)
    except (Session.DoesNotExist, ValueError, TypeError):
        return Response(
            {
                'status': 'INVALID',
                'message': 'Session not found',
                'employee': None,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if session.status == 'cancelled':
        return Response(
            {
                'status': 'INVALID',
                'message': 'Session is cancelled',
                'employee': None,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        employee = EmployeeCredential.objects.select_related('chapter').get(credential=credential)
    except EmployeeCredential.DoesNotExist:
        ScanLog.objects.create(
            credential=credential,
            status='NOT_FOUND',
            device_id=device_id,
            session=session,
        )
        return Response(
            {
                'status': 'NOT_FOUND',
                'message': 'No employee found with this credential',
                'employee': None,
            },
            status=status.HTTP_200_OK,
        )

    if not employee.chapter_id or employee.chapter_id != session.chapter_id:
        ScanLog.objects.create(
            employee=employee,
            credential=credential,
            status='WRONG_CHAPTER',
            device_id=device_id,
            session=session,
        )
        return Response(
            {
                'status': 'WRONG_CHAPTER',
                'message': 'Employee is not a member of this session chapter',
                'employee': EmployeeCredentialSerializer(employee).data,
            },
            status=status.HTTP_200_OK,
        )

    if SessionAttendance.objects.filter(session=session, employee=employee).exists():
        ScanLog.objects.create(
            employee=employee,
            credential=credential,
            status='DUPLICATE',
            device_id=device_id,
            session=session,
        )
        return Response(
            {
                'status': 'DUPLICATE',
                'message': 'This employee has already scanned for this session',
                'employee': EmployeeCredentialSerializer(employee).data,
            },
            status=status.HTTP_200_OK,
        )

    SessionAttendance.objects.create(
        session=session,
        employee=employee,
        device_id=device_id,
    )
    ScanLog.objects.create(
        employee=employee,
        credential=credential,
        status='SUCCESS',
        device_id=device_id,
        session=session,
    )

    return Response(
        {
            'status': 'SUCCESS',
            'message': 'Attendance marked successfully',
            'employee': EmployeeCredentialSerializer(employee).data,
        },
        status=status.HTTP_200_OK,
    )
