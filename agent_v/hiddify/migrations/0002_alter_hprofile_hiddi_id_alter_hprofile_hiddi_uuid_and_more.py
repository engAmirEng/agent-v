# Generated by Django 4.2.3 on 2023-07-06 18:57

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("hiddify", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="hprofile",
            name="hiddi_id",
            field=models.PositiveIntegerField(unique=True),
        ),
        migrations.AlterField(
            model_name="hprofile",
            name="hiddi_uuid",
            field=models.UUIDField(unique=True),
        ),
        migrations.AlterField(
            model_name="hprofile",
            name="user",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE, related_name="user_hprofile", to=settings.AUTH_USER_MODEL
            ),
        ),
    ]
