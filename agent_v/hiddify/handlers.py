import jdatetime
from django.template.loader import get_template
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message

from agent_v.seller.models import Plan
from agent_v.telebot.utils import DataType

from .models import HiddiUser, HProfile


async def profile(update: Message, data: DataType, bot: AsyncTeleBot) -> None:
    user = data["user"]
    try:
        h_profile = await HProfile.objects.aget(user=user)
    except HProfile.DoesNotExist:
        await bot.send_message(update.chat.id, "شما هنوز خریدی از بات انجام نداده اید")
        return
    hiddi_user = await HiddiUser.objects.using("hiddi").aget(uuid=str(h_profile.hiddi_uuid))

    current_plan = await Plan.objects.get_current_active_for_user(user=user)
    remained_data = hiddi_user.get_remained_data()
    expiry_time = jdatetime.date.fromgregorian(date=hiddi_user.get_expiry_time())

    text = get_template("hiddify/profile_text.html").render(
        {"plan_title": current_plan.title, "remained_data": remained_data, "expiry_time": expiry_time}
    )
    await bot.send_message(update.chat.id, text)
