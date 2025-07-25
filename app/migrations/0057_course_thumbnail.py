# Generated by Django 5.1.6 on 2025-07-21 13:49

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0056_examtype_icon'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='thumbnail',
            field=models.ImageField(blank=True, null=True, upload_to='courses/thumbnails/', validators=[django.core.validators.FileExtensionValidator(['jpg', 'png', 'jpeg'])]),
        ),
    ]
