import asyncio

from django.conf import settings
from django.core.management.base import BaseCommand
from telebot import asyncio_helper
from telebot.async_telebot import AsyncTeleBot

from agent_v.telebot.routes import routes


class Command(BaseCommand):
    help = "Start telegram bot with polling"

    def handle(self, *args, **options):
        tb = AsyncTeleBot(settings.BOT_TOKEN)
        if settings.PROXY_URL:
            asyncio_helper.proxy = settings.PROXY_URL
        routes(tb)
        self.stdout.write(self.style.SUCCESS("Successfully started to poll ..."))
        asyncio.run(tb.infinity_polling())
