# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from datetime import date, timedelta
from decimal import Decimal

from django.db import models


class AdminUser(models.Model):
    uuid = models.CharField()
    name = models.CharField()
    mode = models.CharField()
    can_add_admin = models.BooleanField()
    max_users = models.IntegerField()
    max_active_users = models.IntegerField()
    comment = models.CharField(blank=True, null=True)
    telegram_id = models.CharField(blank=True, null=True)
    parent_admin = models.ForeignKey("self", models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "admin_user"


class BoolConfig(models.Model):
    child = models.OneToOneField(
        "Child", models.DO_NOTHING, primary_key=True
    )  # The composite primary key (child_id, key) found, that is not supported. The first column is selected.
    key = models.CharField()
    value = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "bool_config"


class Child(models.Model):
    unique_id = models.CharField()

    class Meta:
        managed = False
        db_table = "child"


class DailyUsage(models.Model):
    date = models.DateField(blank=True, null=True)
    usage = models.BigIntegerField()
    online = models.IntegerField()
    admin = models.ForeignKey(AdminUser, models.DO_NOTHING)
    child = models.ForeignKey(Child, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "daily_usage"


class Domain(models.Model):
    child = models.ForeignKey(Child, models.DO_NOTHING, blank=True, null=True)
    domain = models.CharField()
    alias = models.CharField(blank=True, null=True)
    sub_link_only = models.BooleanField()
    mode = models.CharField()
    cdn_ip = models.TextField(blank=True, null=True)
    grpc = models.BooleanField(blank=True, null=True)
    servernames = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "domain"


class ParentDomain(models.Model):
    domain = models.CharField()
    alias = models.CharField()

    class Meta:
        managed = False
        db_table = "parent_domain"


class Proxy(models.Model):
    child = models.ForeignKey(Child, models.DO_NOTHING, blank=True, null=True)
    name = models.CharField()
    enable = models.BooleanField()
    proto = models.CharField()
    l3 = models.CharField()
    transport = models.CharField()
    cdn = models.CharField()

    class Meta:
        managed = False
        db_table = "proxy"


class ShowDomain(models.Model):
    domain = models.OneToOneField(
        Domain, models.DO_NOTHING, primary_key=True
    )  # The composite primary key (domain_id, related_id) found, that is not supported. The first column is selected.
    related = models.ForeignKey(Domain, models.DO_NOTHING, related_name="showdomain_related_set")

    class Meta:
        managed = False
        db_table = "show_domain"


class ShowDomainParent(models.Model):
    domain = models.OneToOneField(
        ParentDomain, models.DO_NOTHING, primary_key=True
    )  # The composite primary key (domain_id, related_id) found, that is not supported. The first column is selected.
    related = models.ForeignKey(Domain, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "show_domain_parent"


class StrConfig(models.Model):
    child = models.OneToOneField(
        Child, models.DO_NOTHING, primary_key=True
    )  # The composite primary key (child_id, key) found, that is not supported. The first column is selected.
    key = models.CharField()
    value = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "str_config"


class HiddiUser(models.Model):
    uuid = models.CharField()
    name = models.CharField()
    last_online = models.DateTimeField()
    expiry_time = models.DateField(blank=True, null=True)
    usage_limit_gb = models.TextField(
        db_column="usage_limit_GB"
    )  # Field name made lowercase. This field type is a guess.
    package_days = models.IntegerField()
    mode = models.CharField()
    monthly = models.BooleanField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    current_usage_gb = models.TextField(
        db_column="current_usage_GB"
    )  # Field name made lowercase. This field type is a guess.
    last_reset_time = models.DateField(blank=True, null=True)
    comment = models.CharField(blank=True, null=True)
    telegram_id = models.CharField(blank=True, null=True)
    added_by = models.ForeignKey(AdminUser, models.DO_NOTHING, db_column="added_by", blank=True, null=True)
    max_ips = models.IntegerField()
    enable = models.BooleanField()

    class Meta:
        managed = False
        db_table = "user"

    def get_remained_data(self) -> Decimal:
        return Decimal(self.usage_limit_gb) - Decimal(self.current_usage_gb)

    def get_expiry_time(self) -> date:
        return self.start_date + timedelta(days=self.package_days)


class UserDetail(models.Model):
    user = models.ForeignKey(HiddiUser, models.DO_NOTHING)
    child = models.ForeignKey(Child, models.DO_NOTHING)
    last_online = models.DateTimeField()
    current_usage_gb = models.TextField(
        db_column="current_usage_GB"
    )  # Field name made lowercase. This field type is a guess.
    connected_ips = models.CharField()

    class Meta:
        managed = False
        db_table = "user_detail"
