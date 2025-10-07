from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("project", "0003_tasktimelog"),
    ]

    operations = [
        migrations.AddField(
            model_name="timesheet",
            name="auto_logged",
            field=models.BooleanField(default=False, verbose_name="Auto Logged"),
        ),
    ]
