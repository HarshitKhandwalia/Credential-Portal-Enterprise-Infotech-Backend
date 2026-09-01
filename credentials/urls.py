from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import (
    EmployeeViewSet,
    generate_QR_passes,
    health_check,
    send_credential_invite,
    scan_credential,  # ADD THIS
)
from .wallet_views import (
    wallet_apple_detail,
    wallet_apple_generate,
    wallet_google_detail,
    wallet_google_generate,
)

router = DefaultRouter()
router.register(r'credentials', EmployeeViewSet, basename='credential')

urlpatterns = [
    path('health/', health_check, name='health-check'),
    path('', include(router.urls)),
    path('credentials/<int:pk>/send/', send_credential_invite, name='send-credential'),
    path(
        'credentials/<int:pk>/generate-qr-passes/',
        generate_QR_passes,
        name='generate-qr-passes',
    ),
    path('credentials/scan/', scan_credential, name='scan-credential'),  # ADD THIS
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