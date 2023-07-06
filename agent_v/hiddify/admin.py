from django.contrib import admin

from agent_v.hiddify.models import HProfile


@admin.register(HProfile)
class HProfileAdmin(admin.ModelAdmin):
    pass
