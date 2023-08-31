import re
from typing import Union

from telebot.async_telebot import AsyncTeleBot
from telebot.types import CallbackQuery, Message

from agent_v.seller.handlers import check_payment, deliver_payment, dont_deliver_payment_yet, get_plan, profile, start
from agent_v.telebot.handlers import hello, log_error


def regex_match(pattern: str):
    def wrapper(update: Union[Message, CallbackQuery]):
        return re.match(pattern, update.data if type(update) == CallbackQuery else update.text)

    return wrapper


def routes(tb: AsyncTeleBot):
    tb.message_handler(commands=["start"])(start),
    tb.message_handler(commands=["profile"])(profile),
    tb.callback_query_handler(regex_match(r"get_plan/(\d+)"))(get_plan),
    tb.callback_query_handler(regex_match(r"check_payment/(\d+)"))(check_payment),
    tb.callback_query_handler(regex_match(r"deliver_payment/(\d+)"))(deliver_payment),
    tb.callback_query_handler(regex_match(r"dont_deliver_payment_yet/(\d+)"))(dont_deliver_payment_yet),
    tb.message_handler(commands=["hello"])(hello),
    tb.message_handler(commands=["log_error"])(log_error),
