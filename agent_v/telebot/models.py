from typing import Optional

from asgiref.sync import async_to_sync, sync_to_async
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models, transaction

from agent_v.users.models import RepresentativeCode

User = get_user_model()


class ProfileManager(models.Manager):
    @sync_to_async
    @transaction.atomic
    def create_in_start_bot(self, username: str, bot_user_id: int, repr_code: Optional[str]):
        user = User()
        user.username = async_to_sync(self.generate_user_username)(username)
        user.save()
        profile = self.model()
        profile.user = user
        profile.bot_user_id = bot_user_id
        profile.save()
        if repr_code:
            async_to_sync(RepresentativeCode.objects.use_for)(repr_code, user)
        return profile

    @staticmethod
    async def generate_user_username(preferred_user_name):
        last_user = await User.objects.order_by("id").alast()
        last_user_id = last_user.id if last_user else 0
        return f"{preferred_user_name}#{last_user_id+1}"

    async def change_rc_code(self, user: User, rc_code: RepresentativeCode):
        try:
            perv = await RepresentativeCode.objects.aget(used_by=user)
        except RepresentativeCode.DoesNotExist:
            pass
        else:
            await perv.used_by.aremove(user)
        await rc_code.used_by.aadd(user)


class Profile(models.Model):
    objects = ProfileManager()

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_botprofile")
    bot_user_id = models.BigIntegerField()
