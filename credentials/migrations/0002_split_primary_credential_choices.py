from django.db import migrations, models


def forwards_split_primary_credential(apps, schema_editor):
    EmployeeCredential = apps.get_model('credentials', 'EmployeeCredential')
    EmployeeCredential.objects.filter(primary_credential='QR / NFC').update(primary_credential='QR')


def backwards_split_primary_credential(apps, schema_editor):
    EmployeeCredential = apps.get_model('credentials', 'EmployeeCredential')
    EmployeeCredential.objects.filter(primary_credential__in=['QR', 'NFC']).update(
        primary_credential='QR / NFC'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('credentials', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(forwards_split_primary_credential, backwards_split_primary_credential),
        migrations.AlterField(
            model_name='employeecredential',
            name='primary_credential',
            field=models.CharField(
                choices=[('QR', 'QR'), ('NFC', 'NFC')],
                default='QR',
                max_length=50,
            ),
        ),
    ]
