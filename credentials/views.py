from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .delivery import deliver_wallet_links
from .models import (
    Chapter,
    EmployeeCredential,
    ScanLog,
    Session,
    SessionAttendance,
    Substitute,
    Visitor,
)
from .serializers import (
    ChapterSerializer,
    EmployeeCredentialListSerializer,
    EmployeeCredentialSerializer,
    EmployeeSummarySerializer,
    RecurringSessionCreateSerializer,
    SessionSerializer,
    SubstituteSerializer,
    VisitorSerializer,
    VisitorSubstituteCreateSerializer,
    VisitorSubstituteSendSerializer,
    WalletChannelsSerializer,
)
from .utils import (
    MAX_RECURRING_SESSIONS,
    format_session_title,
    generate_weekly_occurrences,
)
from .wallet_tokens import (
    PASS_KIND_SUBSTITUTE,
    PASS_KIND_VISITOR,
    build_employee_wallet_urls,
    build_wallet_urls,
)


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

    @action(detail=True, methods=['post'], url_path='sessions/recurring')
    def recurring_sessions(self, request, pk=None):
        """
        Create weekly sessions up front (same weekday as starts_at) until recurrence_end_date.
        Caps at 10 sessions. Titles are '{series title} — {date}'.
        """
        chapter = self.get_object()
        serializer = RecurringSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            slots = list(
                generate_weekly_occurrences(
                    data['starts_at'],
                    data['ends_at'],
                    data['recurrence_end_date'],
                    max_sessions=MAX_RECURRING_SESSIONS,
                )
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if not slots:
            return Response(
                {'detail': 'No sessions fall within the given date range.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        series_title = data.get('title') or ''
        session_status = data.get('status') or 'scheduled'
        created = [
            Session(
                chapter=chapter,
                title=format_session_title(series_title, slot_start),
                starts_at=slot_start,
                ends_at=slot_end,
                status=session_status,
            )
            for slot_start, slot_end in slots
        ]
        Session.objects.bulk_create(created)

        # bulk_create may not set PKs on all DBs the same way; reload for response.
        created_ids = [s.pk for s in created if s.pk]
        if created_ids:
            sessions = Session.objects.filter(pk__in=created_ids).order_by('starts_at')
        else:
            # Fallback: match by chapter + starts_at window
            sessions = Session.objects.filter(
                chapter=chapter,
                starts_at__in=[slot[0] for slot in slots],
            ).order_by('starts_at')

        return Response(
            {
                'count': sessions.count(),
                'capped_at': MAX_RECURRING_SESSIONS,
                'sessions': SessionSerializer(sessions, many=True).data,
            },
            status=status.HTTP_201_CREATED,
        )


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

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == 'list':
            qs = qs.prefetch_related(
                Prefetch(
                    'issued_visitors',
                    queryset=Visitor.objects.select_related('session', 'member').order_by('-created_at'),
                ),
                Prefetch(
                    'issued_substitutes',
                    queryset=Substitute.objects.select_related('session', 'member').order_by('-created_at'),
                ),
            )
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return EmployeeCredentialListSerializer
        return EmployeeCredentialSerializer


def get_view_name(self):
    return "Credentials list"


@api_view(['POST'])
def generate_QR_passes(request, pk):
    """
    Send wallet links for a member.

    Body (optional): {"channels": ["email", "whatsapp"]}
    Omitted channels means email only, matching existing clients.
    When channels is sent, both results are returned even if one fails.
    """
    try:
        employee = EmployeeCredential.objects.get(pk=pk)
    except EmployeeCredential.DoesNotExist:
        return Response(
            {'error': 'Credential not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    channel_serializer = WalletChannelsSerializer(data=request.data)
    if not channel_serializer.is_valid():
        return Response(channel_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    channels = channel_serializer.validated_data.get('channels') or ['email']
    explicit_channels = 'channels' in channel_serializer.validated_data
    wallet_urls = build_employee_wallet_urls(employee)
    delivery = deliver_wallet_links(
        name=employee.name,
        email=employee.email,
        phone=employee.phone,
        wallet_urls=wallet_urls,
        channels=channels,
    )

    if not explicit_channels:
        if not delivery.get('email_sent'):
            error = delivery.get('errors', {}).get('email', 'Failed to send wallet email.')
            status_code = (
                status.HTTP_400_BAD_REQUEST
                if not employee.email
                else status.HTTP_502_BAD_GATEWAY
            )
            body = {'error': error, 'employee_id': employee.pk}
            if employee.email:
                body['wallet_urls'] = wallet_urls
            return Response(body, status=status_code)
        return Response(
            {
                'employee_id': employee.pk,
                'email_sent': True,
                'wallet_urls': wallet_urls,
            },
            status=status.HTTP_200_OK,
        )

    delivery['employee_id'] = employee.pk
    return Response(delivery, status=status.HTTP_200_OK)


@api_view(['POST'])
def send_credential_invite(request, pk):
    try:
        employee = EmployeeCredential.objects.get(pk=pk)
    except EmployeeCredential.DoesNotExist:
        return Response({'error': 'Credential not found'}, status=status.HTTP_404_NOT_FOUND)

    # Only overwrite contact fields when the client sends a non-empty value.
    # Frontend often sends phone/email as null, which previously wiped seeded data.
    if 'email' in request.data:
        email = request.data.get('email')
        if isinstance(email, str):
            email = email.strip() or None
        if email:
            employee.email = email

    if 'phone' in request.data:
        phone = request.data.get('phone')
        if isinstance(phone, str):
            phone = phone.strip() or None
        if phone:
            employee.phone = phone

    employee.status = 'invite_sent'
    employee.save()

    serializer = EmployeeCredentialSerializer(employee)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
def scan_credential(request):
    """
    Scan a 6-digit credential for a specific session.

    Tries member first, then visitor, then substitute for the session.

    Input: {"credential": "849201", "session_id": 12, "device_id": "gate-1"}
    """
    credential = str(request.data.get('credential', '')).strip()
    device_id = request.data.get('device_id', None)
    session_id = request.data.get('session_id', None)

    if not credential or not credential.isdigit() or len(credential) != 6:
        return Response(
            {
                'status': 'INVALID',
                'message': 'Credential must be 6 digits',
                'type': None,
                'employee': None,
                'data': None,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if session_id is None:
        return Response(
            {
                'status': 'INVALID',
                'message': 'session_id is required',
                'type': None,
                'employee': None,
                'data': None,
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
                'type': None,
                'employee': None,
                'data': None,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if session.status == 'cancelled':
        return Response(
            {
                'status': 'INVALID',
                'message': 'Session is cancelled',
                'type': None,
                'employee': None,
                'data': None,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    employee = (
        EmployeeCredential.objects.select_related('chapter')
        .filter(credential=credential)
        .first()
    )
    if employee is not None:
        return _scan_member(employee, session, credential, device_id)

    visitor_or_sub_response = _scan_visitor_or_substitute(session, credential, device_id)
    if visitor_or_sub_response is not None:
        return visitor_or_sub_response

    ScanLog.objects.create(
        credential=credential,
        status='NOT_FOUND',
        device_id=device_id,
        session=session,
    )
    return Response(
        {
            'status': 'NOT_FOUND',
            'message': 'No member, visitor, or substitute found with this credential',
            'type': None,
            'employee': None,
            'data': None,
        },
        status=status.HTTP_200_OK,
    )


def _scan_member(employee, session, credential, device_id):
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
                'type': 'member',
                'employee': EmployeeCredentialSerializer(employee).data,
                'data': None,
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
                'type': 'member',
                'employee': EmployeeCredentialSerializer(employee).data,
                'data': None,
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
            'type': 'member',
            'employee': EmployeeCredentialSerializer(employee).data,
            'data': None,
        },
        status=status.HTTP_200_OK,
    )


def _scan_visitor_or_substitute(session, credential, device_id):
    visitor = Visitor.objects.filter(session=session, credential=credential).first()
    if visitor is not None:
        return _mark_visitor_or_substitute_scan(
            entry=visitor,
            entry_type='visitor',
            session=session,
            credential=credential,
            device_id=device_id,
            serializer_class=VisitorSerializer,
        )

    substitute = Substitute.objects.filter(session=session, credential=credential).first()
    if substitute is not None:
        return _mark_visitor_or_substitute_scan(
            entry=substitute,
            entry_type='substitute',
            session=session,
            credential=credential,
            device_id=device_id,
            serializer_class=SubstituteSerializer,
        )

    return None


def _mark_visitor_or_substitute_scan(
    *,
    entry,
    entry_type,
    session,
    credential,
    device_id,
    serializer_class,
):
    if entry.status == 'cancelled':
        ScanLog.objects.create(
            credential=credential,
            status='INVALID',
            device_id=device_id,
            session=session,
        )
        return Response(
            {
                'status': 'INVALID',
                'message': f'This {entry_type} pass is cancelled',
                'type': entry_type,
                'employee': None,
                'data': serializer_class(entry).data,
            },
            status=status.HTTP_200_OK,
        )

    if entry.status == 'scanned':
        ScanLog.objects.create(
            credential=credential,
            status='DUPLICATE',
            device_id=device_id,
            session=session,
        )
        return Response(
            {
                'status': 'DUPLICATE',
                'message': f'This {entry_type} has already scanned',
                'type': entry_type,
                'employee': None,
                'data': serializer_class(entry).data,
            },
            status=status.HTTP_200_OK,
        )

    entry.status = 'scanned'
    entry.scanned_at = timezone.now()
    entry.save(update_fields=['status', 'scanned_at'])

    ScanLog.objects.create(
        credential=credential,
        status='SUCCESS',
        device_id=device_id,
        session=session,
    )

    return Response(
        {
            'status': 'SUCCESS',
            'message': f'{entry_type.capitalize()} attendance marked',
            'type': entry_type,
            'employee': None,
            'data': serializer_class(entry).data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
def create_visitor_substitute(request, session_id):
    """
    Create a visitor or substitute for a session
    Input: {"type": "visitor"|"substitute", "name": "...", "email": "...", "phone": "..."}
    """
    try:
        session = Session.objects.get(id=session_id)
    except Session.DoesNotExist:
        return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = VisitorSubstituteCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    visitor_type = serializer.validated_data['type']
    name = serializer.validated_data['name']
    email = serializer.validated_data.get('email')
    phone = serializer.validated_data.get('phone')

    # Get member from request (who is issuing this)
    member_id = request.data.get('member_id')
    if not member_id:
        return Response({'error': 'member_id required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        member = EmployeeCredential.objects.get(id=member_id)
    except EmployeeCredential.DoesNotExist:
        return Response({'error': 'Member not found'}, status=status.HTTP_404_NOT_FOUND)

    try:
        if visitor_type == 'visitor':
            obj = Visitor.objects.create(
                session=session,
                member=member,
                name=name,
                email=email,
                phone=phone,
            )
            serializer = VisitorSerializer(obj)
        else:  # substitute
            obj = Substitute.objects.create(
                session=session,
                member=member,
                name=name,
                email=email,
                phone=phone,
            )
            serializer = SubstituteSerializer(obj)

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def send_visitor_substitute_passes(request, session_id, pk):
    """
    Send Apple/Google wallet links for a visitor or substitute.

    Body: {"type": "visitor"|"substitute", "channels": ["email", "whatsapp"]}
    Omitted channels means email only. When channels is sent, both results
    are returned even if one fails.
    """
    try:
        session = Session.objects.get(id=session_id)
    except Session.DoesNotExist:
        return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = VisitorSubstituteSendSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    entry_type = serializer.validated_data['type']

    if entry_type == 'visitor':
        try:
            entry = Visitor.objects.get(pk=pk, session=session)
        except Visitor.DoesNotExist:
            return Response({'error': 'Visitor not found'}, status=status.HTTP_404_NOT_FOUND)
        pass_kind = PASS_KIND_VISITOR
        response_serializer = VisitorSerializer
    else:
        try:
            entry = Substitute.objects.get(pk=pk, session=session)
        except Substitute.DoesNotExist:
            return Response({'error': 'Substitute not found'}, status=status.HTTP_404_NOT_FOUND)
        pass_kind = PASS_KIND_SUBSTITUTE
        response_serializer = SubstituteSerializer

    channels = serializer.validated_data.get('channels') or ['email']
    explicit_channels = 'channels' in serializer.validated_data
    wallet_urls = build_wallet_urls(pass_kind, entry.pk)
    delivery = deliver_wallet_links(
        name=entry.name,
        email=entry.email,
        phone=entry.phone,
        wallet_urls=wallet_urls,
        channels=channels,
    )
    sent = delivery.get('email_sent') or delivery.get('whatsapp_sent')

    if sent:
        entry.sent_at = timezone.now()
        entry.save(update_fields=['sent_at'])

    if not explicit_channels:
        if not delivery.get('email_sent'):
            error = delivery.get('errors', {}).get('email', 'Failed to send wallet email.')
            status_code = (
                status.HTTP_400_BAD_REQUEST
                if not entry.email
                else status.HTTP_502_BAD_GATEWAY
            )
            body = {'error': error, 'type': entry_type, 'id': entry.pk}
            if entry.email:
                body['wallet_urls'] = wallet_urls
            return Response(body, status=status_code)
        return Response(
            {
                'type': entry_type,
                'id': entry.pk,
                'email_sent': True,
                'wallet_urls': wallet_urls,
                'data': response_serializer(entry).data,
            },
            status=status.HTTP_200_OK,
        )

    delivery['type'] = entry_type
    delivery['id'] = entry.pk
    delivery['data'] = response_serializer(entry).data
    return Response(delivery, status=status.HTTP_200_OK)


@api_view(['DELETE'])
def delete_visitor_substitute(request, session_id, pk):
    """
    Delete a visitor or substitute for a session.
    Body: {"type": "visitor"|"substitute"}
    """
    try:
        session = Session.objects.get(id=session_id)
    except Session.DoesNotExist:
        return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = VisitorSubstituteSendSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    entry_type = serializer.validated_data['type']

    if entry_type == 'visitor':
        try:
            entry = Visitor.objects.get(pk=pk, session=session)
        except Visitor.DoesNotExist:
            return Response({'error': 'Visitor not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        try:
            entry = Substitute.objects.get(pk=pk, session=session)
        except Substitute.DoesNotExist:
            return Response({'error': 'Substitute not found'}, status=status.HTTP_404_NOT_FOUND)

    entry_id = entry.pk
    entry.delete()

    return Response(
        {
            'type': entry_type,
            'id': entry_id,
            'deleted': True,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['PATCH'])
def scan_visitor_substitute(request, session_id, credential):
    """
    Scan a visitor or substitute credential
    Input: {"device_id": "gate-1"}
    """
    try:
        session = Session.objects.get(id=session_id)
    except Session.DoesNotExist:
        return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)

    device_id = request.data.get('device_id', None)

    # Try visitor first
    visitor = Visitor.objects.filter(session=session, credential=credential).first()
    if visitor:
        if visitor.status == 'scanned':
            return Response({
                'status': 'DUPLICATE',
                'message': 'This visitor has already scanned',
                'type': 'visitor',
                'data': VisitorSerializer(visitor).data,
            })

        visitor.status = 'scanned'
        visitor.scanned_at = timezone.now()
        visitor.save()

        return Response({
            'status': 'SUCCESS',
            'message': 'Visitor attendance marked',
            'type': 'visitor',
            'data': VisitorSerializer(visitor).data,
        })

    # Try substitute
    substitute = Substitute.objects.filter(session=session, credential=credential).first()
    if substitute:
        if substitute.status == 'scanned':
            return Response({
                'status': 'DUPLICATE',
                'message': 'This substitute has already scanned',
                'type': 'substitute',
                'data': SubstituteSerializer(substitute).data,
            })

        substitute.status = 'scanned'
        substitute.scanned_at = timezone.now()
        substitute.save()

        return Response({
            'status': 'SUCCESS',
            'message': 'Substitute attendance marked',
            'type': 'substitute',
            'data': SubstituteSerializer(substitute).data,
        })

    # Not found
    return Response({
        'status': 'NOT_FOUND',
        'message': 'Visitor or substitute not found',
    }, status=status.HTTP_404_NOT_FOUND)