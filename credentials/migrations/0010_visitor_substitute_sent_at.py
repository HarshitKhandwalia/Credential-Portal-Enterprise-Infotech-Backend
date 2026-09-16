from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('credentials', '0009_substitute_visitor'),
    ]

    operations = [
        migrations.AddField(
            model_name='substitute',
            name='sent_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='visitor',
            name='sent_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
