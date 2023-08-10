import re
from typing import Literal, Union

from telebot.async_telebot import AsyncTeleBot
from telebot.types import CallbackQuery, Message

from agent_v.seller.handlers import (
    STATES,
    admin,
    check_payment,
    deliver_payment,
    dont_deliver_payment_yet,
    get_plan,
    manual_payment,
    profile,
    profile_action,
    search_users,
    start,
)
from agent_v.telebot.handlers import hello, log_error


def regex_match(pattern: str, on: Literal["text", "state"] = "text", bot: AsyncTeleBot = None):
    async def wrapper(update: Union[Message, CallbackQuery]):
        if on == "text":
            return re.match(pattern, update.data if type(update) == CallbackQuery else update.text)
        elif on == "state":
            state = await bot.get_state(
                user_id=update.from_user.id,
                chat_id=update.message.chat.id if type(update) == CallbackQuery else update.chat.id,
            )
            return re.match(pattern, state)
        raise Exception("pass text or state")

    return wrapper


def routes(tb: AsyncTeleBot):
    tb.message_handler(commands=["start"])(start),
    tb.message_handler(commands=["profile"])(profile),
    tb.callback_query_handler(regex_match(r"get_plan/(\d+)"))(get_plan),
    tb.callback_query_handler(regex_match(r"check_payment/(\d+)"))(check_payment),
    tb.callback_query_handler(regex_match(r"deliver_payment/(\d+)"))(deliver_payment),
    tb.callback_query_handler(regex_match(r"dont_deliver_payment_yet/(\d+)"))(dont_deliver_payment_yet),
    tb.message_handler(commands=["admin"])(admin),
    tb.callback_query_handler(regex_match(r"^search_users$"))(search_users),
    tb.message_handler(state=STATES.SEARCH_USERS)(search_users),
    tb.callback_query_handler(regex_match(r"profile_action/(\d+)"))(profile_action),
    tb.callback_query_handler(regex_match(r"manual_payment/(\d+)"))(manual_payment),
    tb.message_handler(regex_match(STATES.ADD_CUSTOM_PLAN, on="state", bot=tb))(manual_payment),
    tb.message_handler(commands=["hello"])(hello),
    tb.message_handler(commands=["log_error"])(log_error),
