import uuid
from typing import Optional
from urllib.parse import urlparse

import aiohttp
from aiohttp import ClientTimeout
from django.conf import settings
from pyquery import PyQuery as pq

from agent_v.seller.utils import ProfileDataType

from .models import HiddiUser, HProfile

USER_BASE_URL = "admin/user/"
NEW_USER = USER_BASE_URL + "new/"
EDIT_USER = USER_BASE_URL + "edit/?id={0}"


def get_hiddify_url(url: str):
    return f"{settings.HIDDIFY_URL}/{settings.HIDDIFY_SECRET}/{settings.HIDDIFY_AGENT_UUID}/{url}"


async def create_new_account(user, days: int, volume: int, comment: str):
    """Creates user in the hiddify panel"""
    async with aiohttp.ClientSession(timeout=ClientTimeout(30)) as session:
        new_user_url = get_hiddify_url(NEW_USER)
        _uuid = str(uuid.uuid4())
        async with session.post(
            new_user_url,
            data={
                "uuid": _uuid,
                "name": user.username,
                "usage_limit_GB": volume,
                "package_days": days,
                "mode": "no_reset",
                "comment": comment,
                "enable": True,
            },
            allow_redirects=False,
        ) as r:
            if r.status != 302:
                raise Exception(r.status)
        search_user_url = get_hiddify_url(USER_BASE_URL)
        async with session.get(search_user_url, params={"search": _uuid}, allow_redirects=False) as r:
            edit_url = pq(await r.text())("a[title='ویرایش رکورد']").attr("href")
        id = urlparse(edit_url).query.split("&")[0].split("=")[1]
        _ = await HProfile.objects.new(user=user, _uuid=_uuid, id=id)


async def charge_account(hiddi_id: int, days: int, volume: int, comment: str):
    """Updates user in the hiddify panel"""
    async with aiohttp.ClientSession(timeout=ClientTimeout(25)) as session:
        edit_user_url = get_hiddify_url(EDIT_USER.format(hiddi_id))
        async with session.post(
            edit_user_url,
            data={
                "usage_limit_GB": volume,
                "package_days": days,
                "mode": "no_reset",
                "comment": comment,
                "enable": True,
                "reset_days": True,
                "reset_usage": True,
            },
            allow_redirects=False,
        ) as r:
            if r.status != 302:
                raise Exception(r.status)


async def get_profile(user) -> Optional[ProfileDataType]:
    from agent_v.seller.models import Plan

    try:
        h_profile = await HProfile.objects.aget(user=user)
    except HProfile.DoesNotExist:
        return None
    hiddi_user = await HiddiUser.objects.using("hiddi").aget(uuid=str(h_profile.hiddi_uuid))

    current_plan = await Plan.objects.get_current_active_for_user(user=user)
    remained_data = hiddi_user.get_remained_data()
    expiry_date = hiddi_user.get_expiry_time()
    return {"current_plan": current_plan, "remained_data": remained_data, "expiry_date": expiry_date}
