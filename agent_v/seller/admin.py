from django.contrib import admin

from agent_v.seller.models import CardToCardGate, Payment, Plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    pass


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    pass


@admin.register(CardToCardGate)
class CardToCardGateAdmin(admin.ModelAdmin):
    pass
