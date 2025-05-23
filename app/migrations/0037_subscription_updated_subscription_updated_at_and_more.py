# Generated by Django 5.1.6 on 2025-04-22 08:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0036_alter_subscription_started_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='updated',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='subscription',
            name='updated_at',
            field=models.DateField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='started_at',
            field=models.DateField(auto_now_add=True),
        ),
    ]
