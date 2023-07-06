from telegram.ext import CommandHandler, MessageHandler, filters

from agent_v.telebot.handlers import hello

routes = [CommandHandler("hello", hello), MessageHandler(filters.TEXT & ~filters.COMMAND, hello)]
