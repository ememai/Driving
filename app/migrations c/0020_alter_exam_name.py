# Generated by Django 5.1.6 on 2025-04-04 16:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0019_alter_exam_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exam',
            name='name',
            field=models.CharField(default='001', max_length=100),
        ),
    ]
