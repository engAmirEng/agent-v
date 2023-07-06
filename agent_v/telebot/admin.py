from django.contrib import admin

from agent_v.telebot.models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    pass
