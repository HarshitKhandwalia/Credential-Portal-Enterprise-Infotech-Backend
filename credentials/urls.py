from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ChapterViewSet,
    EmployeeViewSet,
    SessionViewSet,
    generate_QR_passes,
    health_check,
    scan_credential,
    send_credential_invite,
    create_visitor_substitute,
    delete_visitor_substitute,
    scan_visitor_substitute,
    send_visitor_substitute_passes,
)
from .wallet_views import (
    wallet_apple_detail,
    wallet_apple_generate,
    wallet_google_detail,
    wallet_google_generate,
)

router = DefaultRouter()
router.register(r'chapters', ChapterViewSet, basename='chapter')
router.register(r'sessions', SessionViewSet, basename='session')
router.register(r'credentials', EmployeeViewSet, basename='credential')

urlpatterns = [
    path('health/', health_check, name='health-check'),
    # Must be before the router so "scan" is not treated as a credential pk.
    path('credentials/scan/', scan_credential, name='scan-credential'),
    path('', include(router.urls)),
    path('credentials/<int:pk>/send/', send_credential_invite, name='send-credential'),
    path(
        'credentials/<int:pk>/generate-qr-passes/',
        generate_QR_passes,
        name='generate-qr-passes',
    ),
    # Visitor & Substitute routes
    path(
        'sessions/<int:session_id>/visitor-substitute/create/',
        create_visitor_substitute,
        name='create-visitor-substitute',
    ),
    path(
        'sessions/<int:session_id>/visitor-substitute/<int:pk>/send/',
        send_visitor_substitute_passes,
        name='send-visitor-substitute-passes',
    ),
    path(
        'sessions/<int:session_id>/visitor-substitute/<int:pk>/',
        delete_visitor_substitute,
        name='delete-visitor-substitute',
    ),
    path(
        'sessions/<int:session_id>/visitor-substitute/scan/<str:credential>/',
        scan_visitor_substitute,
        name='scan-visitor-substitute',
    ),
    path('wallet/apple/<str:token>/', wallet_apple_detail, name='wallet-apple-detail'),
    path(
        'wallet/apple/<str:token>/generate/',
        wallet_apple_generate,
        name='wallet-apple-generate',
    ),
    path('wallet/google/<str:token>/', wallet_google_detail, name='wallet-google-detail'),
    path(
        'wallet/google/<str:token>/generate/',
        wallet_google_generate,
        name='wallet-google-generate',
    ),
]