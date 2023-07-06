from telegram.ext import CommandHandler, MessageHandler, filters

from name_goes_here.telebot.handlers import hello

routes = [CommandHandler("hello", hello), MessageHandler(filters.TEXT & ~filters.COMMAND, hello)]
