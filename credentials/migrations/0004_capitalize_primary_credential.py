from django.db import migrations, models


def forwards_capitalize_primary_credential(apps, schema_editor):
    EmployeeCredential = apps.get_model('credentials', 'EmployeeCredential')
    EmployeeCredential.objects.filter(primary_credential='qr').update(primary_credential='QR')
    EmployeeCredential.objects.filter(primary_credential='nfc').update(primary_credential='NFC')


def backwards_capitalize_primary_credential(apps, schema_editor):
    EmployeeCredential = apps.get_model('credentials', 'EmployeeCredential')
    EmployeeCredential.objects.filter(primary_credential='QR').update(primary_credential='qr')
    EmployeeCredential.objects.filter(primary_credential='NFC').update(primary_credential='nfc')


class Migration(migrations.Migration):

    dependencies = [
        ('credentials', '0003_alter_employeecredential_primary_credential'),
    ]

    operations = [
        migrations.RunPython(
            forwards_capitalize_primary_credential,
            backwards_capitalize_primary_credential,
        ),
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
