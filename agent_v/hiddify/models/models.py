import enum

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


class Platform(str, enum.Enum):
    V2RAY_N = "v2rayN"
    V2RAY_NG = "v2rayNG"
    FAIR_VPN = "FairVPN"


class HProfile(models.Model):
    objects = HProfileManager()

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_hprofile")
    hiddi_uuid = models.UUIDField(unique=True)
    hiddi_id = models.PositiveIntegerField(unique=True)

    def get_subscriptions_url(self, platform: Platform):
        base_url = f"{settings.HIDDIFY_SUB_URL}/{settings.HIDDIFY_SECRET}/{self.hiddi_uuid}"
        if platform == Platform.V2RAY_N or platform == Platform.V2RAY_NG:
            url = base_url + "/all.txt?name=usersCdn-MKH&asn=MKH&mode=new"
        elif platform == Platform.FAIR_VPN:
            url = base_url + "/all.txt?name=usersCdn&asn=MKH&mode=new&base64=True"
        return url
