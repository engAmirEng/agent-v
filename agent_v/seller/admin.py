from django.contrib import admin

from agent_v.seller.models import Plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    pass
