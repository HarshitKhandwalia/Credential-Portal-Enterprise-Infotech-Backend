import secrets

from django.db import migrations, models


def generate_token():
    return secrets.token_urlsafe(32)


def backfill_profile_tokens(apps, schema_editor):
    EmployeeCredential = apps.get_model('credentials', 'EmployeeCredential')
    existing = set(
        EmployeeCredential.objects.exclude(profile_token__isnull=True)
        .exclude(profile_token='')
        .values_list('profile_token', flat=True)
    )
    for employee in EmployeeCredential.objects.filter(
        models.Q(profile_token__isnull=True) | models.Q(profile_token='')
    ).iterator():
        while True:
            token = generate_token()
            if token not in existing:
                existing.add(token)
                employee.profile_token = token
                employee.save(update_fields=['profile_token'])
                break


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('credentials', '0013_employeecredential_company_linkedin_website'),
    ]

    operations = [
        migrations.AddField(
            model_name='employeecredential',
            name='profile_token',
            field=models.CharField(editable=False, max_length=64, null=True, unique=True),
        ),
        migrations.RunPython(backfill_profile_tokens, noop_reverse),
        migrations.AlterField(
            model_name='employeecredential',
            name='profile_token',
            field=models.CharField(editable=False, max_length=64, unique=True),
        ),
    ]
