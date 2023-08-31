from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from agent_v.users.forms import UserAdminChangeForm, UserAdminCreationForm
from agent_v.users.models import RepresentativeCode

User = get_user_model()


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("name", "email")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    list_display = ["username", "successful_payment_count", "name", "is_superuser"]
    search_fields = ["name"]

    def get_queryset(self, request):
        qs = super().get_queryset(request).an_successful_payment_count()
        return qs

    @admin.display(ordering="successful_payment_count")
    def successful_payment_count(self, user):
        return user.successful_payment_count


@admin.register(RepresentativeCode)
class RepresentativeCodeAdmin(admin.ModelAdmin):
    list_display = ["descriptions", "code_link", "capacity", "remained_cap", "plan_type", "is_active"]
    list_editable = ["capacity", "plan_type", "is_active"]
    list_filter = ["plan_type", "is_active"]
    readonly_fields = ["used_by"]

    def get_queryset(self, request: HttpRequest):
        qs = super().get_queryset(request)
        return qs.an_used_by_count()

    @admin.display(ordering="code")
    def code_link(self, representative_code):
        from agent_v.telebot.apps import async_tb

        tb = async_tb()
        return format_html(
            '<a href="https://t.me/{bot_username}?start=code={code}">{code}</a>',
            bot_username=tb.cached_user.username,
            code=representative_code.code,
        )

    def remained_cap(self, representative_code):
        return representative_code.capacity - representative_code.used_by_count
