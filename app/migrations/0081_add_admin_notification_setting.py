from django.conf import settings
from django.db import migrations, models
import django.core.validators


def create_admin_notification_setting(apps, schema_editor):
    phone_number = getattr(settings, "ADMIN_PHONE_NUMBER", "")
    if phone_number:
        AdminNotificationSetting = apps.get_model("app", "AdminNotificationSetting")
        AdminNotificationSetting.objects.using(schema_editor.connection.alias).get_or_create(
            pk=1,
            defaults={"phone_number": phone_number},
        )


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0080_add_payment_method_settings"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdminNotificationSetting",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "phone_number",
                    models.CharField(
                        help_text="WhatsApp number that receives automated admin notifications.",
                        max_length=20,
                        validators=[
                            django.core.validators.RegexValidator(
                                r"^\+?[\d\s-]{9,19}$",
                                "Enter a valid phone number.",
                            )
                        ],
                    ),
                ),
            ],
            options={
                "verbose_name": "Admin Notification Setting",
                "verbose_name_plural": "Admin Notification Settings",
            },
        ),
        migrations.RunPython(
            create_admin_notification_setting,
            migrations.RunPython.noop,
        ),
    ]
