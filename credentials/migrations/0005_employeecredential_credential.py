import secrets

from django.db import migrations, models


def _generate_unique_code(existing_codes):
    while True:
        code = f"{secrets.randbelow(1_000_000):06d}"
        if code not in existing_codes:
            existing_codes.add(code)
            return code


def forwards_populate_credential(apps, schema_editor):
    EmployeeCredential = apps.get_model('credentials', 'EmployeeCredential')
    existing_codes = set(
        EmployeeCredential.objects.exclude(credential__isnull=True)
        .exclude(credential='')
        .values_list('credential', flat=True)
    )

    for employee in EmployeeCredential.objects.filter(credential__isnull=True):
        employee.credential = _generate_unique_code(existing_codes)
        employee.save(update_fields=['credential'])


def backwards_clear_credential(apps, schema_editor):
    EmployeeCredential = apps.get_model('credentials', 'EmployeeCredential')
    EmployeeCredential.objects.update(credential=None)


class Migration(migrations.Migration):

    dependencies = [
        ('credentials', '0004_capitalize_primary_credential'),
    ]

    operations = [
        migrations.AddField(
            model_name='employeecredential',
            name='credential',
            field=models.CharField(editable=False, max_length=6, null=True, unique=True),
        ),
        migrations.RunPython(forwards_populate_credential, backwards_clear_credential),
        migrations.AlterField(
            model_name='employeecredential',
            name='credential',
            field=models.CharField(editable=False, max_length=6, unique=True),
        ),
    ]
