from django.contrib import admin
from django.http import HttpRequest

from agent_v.hiddify.models import HProfile


@admin.register(HProfile)
class HProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "hiddi_id", "hiddi_uuid"]

    def get_queryset(self, request: HttpRequest):
        qs = super().get_queryset(request)
        return qs.select_related("user")
