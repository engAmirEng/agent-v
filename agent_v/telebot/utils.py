from typing import Union

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from telebot.async_telebot import AsyncTeleBot
from telebot.types import CallbackQuery, Message

User = get_user_model()


def require_user(func):
    """
    A decorator for handlers that passes user as a keyword argument to them
    """

    async def wrapper(update: Union[Message, CallbackQuery], data, bot: AsyncTeleBot):
        try:
            user = await User.objects.get_by_user_bot_id(update.from_user.id)
        except User.DoesNotExist:
            user = AnonymousUser
        return await func(update, data, bot, user=user)

    return wrapper
