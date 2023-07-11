from typing import TypedDict, Union

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import QueryDict
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_handler_backends import BaseMiddleware
from telebot.types import CallbackQuery, Message
from telebot.util import update_types as all_update_types

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


class UserMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
        self.update_types = all_update_types

    async def pre_process(self, update: Union[Message, CallbackQuery], data):
        try:
            user = await User.objects.get_by_user_bot_id(update.from_user.id)
        except User.DoesNotExist:
            user = AnonymousUser
        data["user"] = user

        return None

    async def post_process(self, message, data, exception):
        pass


class DataType(TypedDict):
    user: User


def get_data_from_command(text: str, command: str):
    if len(text.split(" ")) < 2:
        return QueryDict()
    data_qs = text.split(" ")[1]
    return QueryDict(data_qs)
