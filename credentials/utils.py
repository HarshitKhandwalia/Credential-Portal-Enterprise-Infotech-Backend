import secrets


def generate_unique_credential():
    """Return a random 6-digit code unique across all EmployeeCredential records."""
    from .models import EmployeeCredential

    while True:
        code = f"{secrets.randbelow(1_000_000):06d}"
        if not EmployeeCredential.objects.filter(credential=code).exists():
            return code
