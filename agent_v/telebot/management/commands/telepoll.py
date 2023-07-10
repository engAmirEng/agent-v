import asyncio

import redis
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand
from telebot import asyncio_helper
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_filters import StateFilter

from agent_v.telebot.routes import routes
from agent_v.telebot.utils import UserMiddleware

_async_tb = None


def async_tb() -> AsyncTeleBot:
    """
    Use only to just send messages
    """
    global _async_tb
    if _async_tb is None:
        raise ImproperlyConfigured("_async_tb is not populated.")
    return _async_tb


def set_async_tb(tb: AsyncTeleBot):
    """
    Call it only once
    """
    global _async_tb
    if _async_tb is not None:
        raise ImproperlyConfigured("_async_tb already populated.")
    _async_tb = tb


class Command(BaseCommand):
    help = "Start telegram bot with polling"

    def handle(self, *args, **options):
        redis_url_options = redis.connection.parse_url(settings.REDIS_STATE_STORAGE_URL)  # noqa
        tb = AsyncTeleBot(
            settings.BOT_TOKEN,
            # state_storage=StateRedisStorage(
            #     host=redis_url_options["host"], port=redis_url_options["port"], db=redis_url_options["db"]
            # ),
        )
        if settings.PROXY_URL:
            asyncio_helper.proxy = settings.PROXY_URL
        tb.add_custom_filter(StateFilter(tb))
        tb.middlewares.append(UserMiddleware())
        routes(tb)
        self.stdout.write(self.style.SUCCESS("Successfully started to poll ..."))
        set_async_tb(tb)
        asyncio.run(tb.infinity_polling())
