from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models, transaction

User = get_user_model()


class ProfileManager(models.Manager):
    @sync_to_async
    @transaction.atomic
    def create_in_start_bot(self, username: str, bot_user_id: int):
        user = User()
        user.username = username
        user.save()
        profile = self.model()
        profile.user = user
        profile.bot_user_id = bot_user_id
        profile.save()
        return profile


class Profile(models.Model):
    objects = ProfileManager()

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_botprofile")
    bot_user_id = models.BigIntegerField()
