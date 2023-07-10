# Generated by Django 4.2.3 on 2023-07-10 13:26

from django.db import migrations
import django_fsm


class Migration(migrations.Migration):
    dependencies = [
        ("seller", "0004_plan_is_active"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="status",
            field=django_fsm.FSMField(
                choices=[
                    ("PE", "انتظار برای پرداخت"),
                    ("PEA", "انتظار برای تایید ادمین"),
                    ("AR", "رد توسط ادمین"),
                    ("DO", "انجام شده"),
                ],
                max_length=4,
                verbose_name="وضعیت",
            ),
        ),
    ]