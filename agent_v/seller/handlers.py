from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from telebot.async_telebot import AsyncTeleBot
from telebot.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from agent_v.seller.models import Payment, Plan
from agent_v.telebot.models import Profile
from agent_v.telebot.utils import require_user

User = get_user_model()


@require_user
async def start(update: Message, data, bot: AsyncTeleBot, /, user: User) -> None:
    if user.is_anonymous:
        _ = await Profile.objects.create_in_start_bot(
            username=update.from_user.username, bot_user_id=update.from_user.id
        )

    plans = Plan.objects.get_basic()
    markup = InlineKeyboardMarkup()
    plans_buttons = [InlineKeyboardButton(i.title, callback_data=f"get_plan/{i.pk}") async for i in plans]
    markup.add(*plans_buttons, row_width=1)
    await bot.send_message(
        update.chat.id,
        "یکی از پلن ها را انتخاب نمایید",
        reply_markup=markup,
    )


@require_user
async def get_plan(update: CallbackQuery, data, bot: AsyncTeleBot, /, user: User):
    """Attempt to acquire the desired plan"""
    plan_id = update.data.split("/")[1]
    plan = await Plan.objects.get_basic().filter(pk=plan_id).aget()
    payment = await Payment.objects.new_from_bot(plan=plan, user=user)
    keyboard = [
        [
            InlineKeyboardButton(_("پرداخت کردم"), callback_data=f"check_payment/{payment.pk}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await bot.edit_message_text(
        chat_id=update.message.chat.id,
        message_id=update.message.message_id,
        text=_("پرداخت کنید سپس پرداخت کردم را یزنید"),
        reply_markup=reply_markup,
    )


async def check_payment(update: CallbackQuery, data, bot: AsyncTeleBot):
    if True:
        payment_id = update.data.split("/")[1]

        await Payment.deliver(payment_id)
