from django.db import migrations, models


def forwards_populate_membership_id(apps, schema_editor):
    EmployeeCredential = apps.get_model('credentials', 'EmployeeCredential')

    for employee in EmployeeCredential.objects.filter(membership_id__isnull=True):
        employee.membership_id = f"MEM-{employee.pk:05d}"
        employee.save(update_fields=['membership_id'])


def backwards_clear_membership_id(apps, schema_editor):
    EmployeeCredential = apps.get_model('credentials', 'EmployeeCredential')
    EmployeeCredential.objects.update(membership_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ('credentials', '0005_employeecredential_credential'),
    ]

    operations = [
        migrations.AddField(
            model_name='employeecredential',
            name='membership_id',
            field=models.CharField(max_length=100, null=True, unique=True),
        ),
        migrations.RunPython(
            forwards_populate_membership_id,
            backwards_clear_membership_id,
        ),
        migrations.AlterField(
            model_name='employeecredential',
            name='membership_id',
            field=models.CharField(max_length=100, unique=True),
        ),
    ]
