import asyncio

import redis
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand
from telebot import TeleBot, apihelper, asyncio_helper
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_filters import StateFilter

from agent_v.telebot.routes import routes
from agent_v.telebot.utils import UserMiddleware

_sync_tb = None


def sync_tb() -> TeleBot:
    """
    Use only to just send messages
    """
    global _sync_tb
    if _sync_tb is None:
        raise ImproperlyConfigured("_sync_tb is not populated.")
    return _sync_tb


def set_sync_tb(tb: TeleBot):
    """
    Call it only once
    """
    global _sync_tb
    if _sync_tb is not None:
        raise ImproperlyConfigured("_sync_tb already populated.")
    _sync_tb = tb


class Command(BaseCommand):
    help = "Start telegram bot with polling"

    def handle(self, *args, **options):
        set_sync_tb(
            TeleBot(
                settings.BOT_TOKEN,
            )
        )

        redis_url_options = redis.connection.parse_url(settings.REDIS_STATE_STORAGE_URL)  # noqa
        tb = AsyncTeleBot(
            settings.BOT_TOKEN,
            # state_storage=StateRedisStorage(
            #     host=redis_url_options["host"], port=redis_url_options["port"], db=redis_url_options["db"]
            # ),
        )
        if settings.PROXY_URL:
            asyncio_helper.proxy = settings.PROXY_URL
            apihelper.proxy = {"https": settings.PROXY_URL}
        tb.add_custom_filter(StateFilter(tb))
        tb.middlewares.append(UserMiddleware())
        routes(tb)
        self.stdout.write(self.style.SUCCESS("Successfully started to poll ..."))
        asyncio.run(tb.infinity_polling())
