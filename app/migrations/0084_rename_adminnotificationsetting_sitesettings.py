from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0083_consolidate_site_settings"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="AdminNotificationSetting",
            new_name="SiteSettings",
        ),
    ]
