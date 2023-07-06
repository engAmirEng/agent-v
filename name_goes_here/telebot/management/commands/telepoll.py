from django.conf import settings
from django.core.management.base import BaseCommand
from telegram.ext import ApplicationBuilder

from name_goes_here.telebot.routes import routes


class Command(BaseCommand):
    help = "Start telegram bot with polling"

    def handle(self, *args, **options):
        app = ApplicationBuilder().token(settings.BOT_TOKEN)
        if settings.PROXY_URL:
            app = app.proxy_url(settings.PROXY_URL).get_updates_proxy_url(settings.PROXY_URL)
        app = app.build()
        [app.add_handler(handler) for handler in routes]

        self.stdout.write(self.style.SUCCESS("Successfully started to poll ..."))
        app.run_polling()
