# Generated by Django 5.1.6 on 2025-04-06 10:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0021_subscription_super_subscription_alter_exam_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subscription',
            name='duration_days',
            field=models.IntegerField(blank=True, default=1, null=True),
        ),
    ]
