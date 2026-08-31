from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmployeeViewSet, send_credential_invite

router = DefaultRouter()
router.register(r'credentials', EmployeeViewSet, basename='credential')

urlpatterns = [
    path('', include(router.urls)),
    path('credentials/<int:pk>/send/', send_credential_invite, name='send-credential'),
]