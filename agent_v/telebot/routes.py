from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, filters

from agent_v.seller.handlers import check_payment, get_plan, start
from agent_v.telebot.handlers import hello

routes = [
    CommandHandler("start", start),
    CallbackQueryHandler(get_plan, r"get_plan/(\d+)"),
    CallbackQueryHandler(check_payment, r"check_payment/(\d+)"),
    CommandHandler("hello", hello),
    MessageHandler(filters.TEXT & ~filters.COMMAND, hello),
]
