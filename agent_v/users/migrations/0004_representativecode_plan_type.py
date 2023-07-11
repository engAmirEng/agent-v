# Generated by Django 4.2.3 on 2023-07-11 18:45

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0003_representativecode"),
    ]

    operations = [
        migrations.AddField(
            model_name="representativecode",
            name="plan_type",
            field=models.CharField(
                choices=[("def", "default"), ("one", "one"), ("two", "two"), ("three", "three"), ("four", "four")],
                default="def",
                max_length=15,
            ),
        ),
    ]
