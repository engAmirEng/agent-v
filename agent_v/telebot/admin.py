from django.contrib import admin
from django.http import HttpRequest

from agent_v.telebot.models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user"]

    def get_queryset(self, request: HttpRequest):
        qs = super().get_queryset(request)
        return qs.select_related("user")
