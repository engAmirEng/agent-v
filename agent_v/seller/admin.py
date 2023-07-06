from django.contrib import admin

from agent_v.seller.models import Payment, Plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    pass


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    pass
