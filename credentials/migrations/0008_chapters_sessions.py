import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('credentials', '0007_attendance_and_scanlog'),
    ]

    operations = [
        migrations.CreateModel(
            name='Chapter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, default='')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Session',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, default='', max_length=255)),
                ('starts_at', models.DateTimeField()),
                ('ends_at', models.DateTimeField()),
                ('status', models.CharField(
                    choices=[
                        ('scheduled', 'Scheduled'),
                        ('completed', 'Completed'),
                        ('cancelled', 'Cancelled'),
                    ],
                    default='scheduled',
                    max_length=20,
                )),
                ('chapter', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='sessions',
                    to='credentials.chapter',
                )),
            ],
            options={
                'ordering': ['-starts_at'],
            },
        ),
        migrations.AddField(
            model_name='employeecredential',
            name='chapter',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='members',
                to='credentials.chapter',
            ),
        ),
        migrations.CreateModel(
            name='SessionAttendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scanned_at', models.DateTimeField(auto_now_add=True)),
                ('device_id', models.CharField(blank=True, max_length=100, null=True)),
                ('employee', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='session_attendances',
                    to='credentials.employeecredential',
                )),
                ('session', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='attendances',
                    to='credentials.session',
                )),
            ],
            options={
                'ordering': ['-scanned_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='sessionattendance',
            constraint=models.UniqueConstraint(
                fields=('session', 'employee'),
                name='unique_session_employee_attendance',
            ),
        ),
        migrations.AddField(
            model_name='scanlog',
            name='session',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='scan_logs',
                to='credentials.session',
            ),
        ),
        migrations.AlterField(
            model_name='scanlog',
            name='status',
            field=models.CharField(
                choices=[
                    ('SUCCESS', 'Success'),
                    ('DUPLICATE', 'Duplicate'),
                    ('NOT_FOUND', 'Not Found'),
                    ('WRONG_CHAPTER', 'Wrong Chapter'),
                    ('INVALID', 'Invalid'),
                ],
                max_length=20,
            ),
        ),
    ]
