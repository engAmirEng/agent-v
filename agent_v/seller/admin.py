from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from agent_v.seller.models import CardToCardGate, Payment, Plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["title", "plan_type", "price", "volume", "duration", "is_one_time", "is_active", "used_count"]
    list_editable = ["is_active"]
    list_filter = ["plan_type", "is_active"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Plan]:
        qs = super().get_queryset(request).an_used_count()
        return qs

    @admin.display(ordering="used_count")
    def used_count(self, plan):
        return plan.used_count


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["user", "status", "plan_title"]
    list_filter = ["status"]

    def get_queryset(self, request: HttpRequest):
        qs = super().get_queryset(request)
        return qs.select_related("user", "plan")

    @admin.display(ordering="plan")
    def plan_title(self, payment):
        return payment.plan.title


@admin.register(CardToCardGate)
class CardToCardGateAdmin(admin.ModelAdmin):
    list_display = ["admin", "cart_info", "card_number"]

    def get_queryset(self, request: HttpRequest):
        qs = super().get_queryset(request)
        return qs.select_related("admin")
