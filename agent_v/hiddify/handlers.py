import jdatetime
from django.template.loader import get_template
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message

from agent_v.telebot.utils import DataType

from .models import HiddiUser, HProfile


async def profile(update: Message, data: DataType, bot: AsyncTeleBot) -> None:
    user = data["user"]
    h_profile = await HProfile.objects.aget(user=user)
    hiddi_user = await HiddiUser.objects.using("hiddi").aget(uuid=str(h_profile.uuid))
    remained_data = hiddi_user.get_remained_data()
    expiry_time = jdatetime.date.fromgregorian(date=hiddi_user.get_expiry_time())

    text = get_template("hiddify/profile_text.html").render(
        {"remained_data": remained_data, "expiry_time": expiry_time}
    )
    await bot.send_message(update.chat.id, text)
