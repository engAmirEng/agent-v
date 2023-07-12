import asyncio

from django.core.management.base import BaseCommand
from telebot.types import BotCommand

from agent_v.telebot.apps import async_tb


class Command(BaseCommand):
    help = "Start telegram bot with polling"

    def handle(self, *args, **options):
        tb = async_tb()

        async def run():
            await tb.set_my_commands(commands=[BotCommand("start", "منو"), BotCommand("profile", "حجم و تاریخ انقضا")])
            self.stdout.write(self.style.SUCCESS("Successfully started to poll ..."))
            await tb.infinity_polling()

        asyncio.run(run())
