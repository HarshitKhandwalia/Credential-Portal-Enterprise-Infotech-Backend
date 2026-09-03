# Generated manually for merge/qr-scanner-into-main

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('credentials', '0006_employeecredential_membership_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='employeecredential',
            name='attended_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='employeecredential',
            name='is_attended',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='ScanLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('credential', models.CharField(max_length=6)),
                ('status', models.CharField(choices=[('SUCCESS', 'Success'), ('DUPLICATE', 'Duplicate'), ('NOT_FOUND', 'Not Found')], max_length=20)),
                ('device_id', models.CharField(blank=True, max_length=100, null=True)),
                ('scanned_at', models.DateTimeField(auto_now_add=True)),
                ('employee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='credentials.employeecredential')),
            ],
            options={
                'ordering': ['-scanned_at'],
            },
        ),
    ]
