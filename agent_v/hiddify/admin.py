from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest

from agent_v.hiddify.models import HiddiUser, HProfile


@admin.register(HProfile)
class HProfileAdmin(admin.ModelAdmin):
    actions = ["sync_hiddi_id_with_hiddi"]
    list_display = ["user", "hiddi_id", "hiddi_uuid"]

    def get_queryset(self, request: HttpRequest):
        qs = super().get_queryset(request)
        return qs.select_related("user")

    @admin.action
    def sync_hiddi_id_with_hiddi(self, request, queryset: QuerySet[HProfile]):
        """
        hiddify changes user_id without any reason, so we should keep data in sync
        """
        successful_count = 0
        not_found_count = 0
        for i in queryset:
            try:
                hu = HiddiUser.objects.using("hiddi").get(uuid=i.hiddi_uuid)
            except HiddiUser.DoesNotExist:
                not_found_count += 1
                continue
            i.hiddi_id = hu.id
            i.save()
            successful_count += 1
        self.message_user(request, f"total is {queryset.count()}", messages.SUCCESS)
        self.message_user(request, f"{successful_count} are successful", messages.SUCCESS)
        self.message_user(request, f"{not_found_count} are not found", messages.ERROR)
