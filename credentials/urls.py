from django.urls import path
from .views import EmployeeCredentialListCreateView, send_credential_invite

urlpatterns = [
    path('credentials/', EmployeeCredentialListCreateView.as_view(), name='credential-list-create'),
    path('credentials/<int:pk>/send/', send_credential_invite, name='send-credential'),
]