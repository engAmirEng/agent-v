from django.conf import settings
from django.db import models


class HProfileManager(models.Manager):
    async def new(self, user, _uuid, id):
        hprofile = self.model()
        hprofile.user = user
        hprofile.hiddi_uuid = _uuid
        hprofile.hiddi_id = id
        await hprofile.asave()
        return hprofile


class HProfile(models.Model):
    objects = HProfileManager()

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    hiddi_uuid = models.UUIDField()
    hiddi_id = models.PositiveIntegerField()
