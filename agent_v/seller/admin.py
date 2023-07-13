from django.contrib import admin
from django.http import HttpRequest

from agent_v.seller.models import CardToCardGate, Payment, Plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["title", "plan_type", "price", "volume", "duration", "is_active"]
    list_editable = ["is_active"]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["user", "status", "plan_title"]

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
