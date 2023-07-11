import asyncio
import enum

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import get_template
from django.utils.translation import gettext as _
from telebot.async_telebot import AsyncTeleBot
from telebot.types import CallbackQuery, ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, Message

from agent_v.seller.models import Payment, Plan
from agent_v.telebot.models import Profile
from agent_v.telebot.utils import DataType
from agent_v.users.models import RepresentativeCode

User = get_user_model()


class STATES(str, enum.Enum):
    ENTERING_REPRESENTATIVE_CODE = "entering_representative_code"


async def start(update: Message, data: DataType, bot: AsyncTeleBot) -> None:
    user = data["user"]
    if user.is_anonymous:
        if settings.ALLOW_NEW_UNKNOWN:
            _ = await Profile.objects.create_in_start_bot(
                username=update.from_user.username, bot_user_id=update.from_user.id
            )
        else:
            await bot.set_state(
                update.from_user.id,
                STATES.ENTERING_REPRESENTATIVE_CODE.value,
                chat_id=update.chat.id,
            )
            await bot.send_message(update.chat.id, "لطفا کد معرف را وارد نمایید", reply_markup=ForceReply())
            return

    plans = Plan.objects.get_basic()
    markup = InlineKeyboardMarkup()
    plans_buttons = [InlineKeyboardButton(i.title, callback_data=f"get_plan/{i.pk}") async for i in plans]
    markup.add(*plans_buttons, row_width=1)
    text = get_template("seller/choose_plan_text.html").render()
    await bot.send_message(
        update.chat.id,
        text,
        reply_markup=markup,
        parse_mode="html",
    )


async def validate_representative_code(update: Message, data: DataType, bot: AsyncTeleBot):
    a_moment_message = await bot.send_message(
        update.chat.id,
        "چند لحظه ...",
    )
    await asyncio.sleep(settings.VALIDATE_DELAY)  # to prevent brute force
    is_valid, reason = await RepresentativeCode.objects.validate_code(update.text)
    if not is_valid:
        await bot.edit_message_text(
            f"با این کد امکان دسترسی ندارید، {reason}",
            chat_id=a_moment_message.chat.id,
            message_id=a_moment_message.message_id,
        )
        return
    await bot.delete_state(update.from_user.id, chat_id=update.chat.id)
    _ = await Profile.objects.create_in_start_bot(
        username=update.from_user.username, bot_user_id=update.from_user.id, repr_code=update.text
    )
    plans = Plan.objects.get_basic()
    markup = InlineKeyboardMarkup()
    plans_buttons = [InlineKeyboardButton(i.title, callback_data=f"get_plan/{i.pk}") async for i in plans]
    markup.add(*plans_buttons, row_width=1)
    text = get_template("seller/choose_plan_text.html").render()
    await bot.edit_message_text(
        text,
        chat_id=a_moment_message.chat.id,
        message_id=a_moment_message.message_id,
        reply_markup=markup,
        parse_mode="html",
    )


async def get_plan(update: CallbackQuery, data: DataType, bot: AsyncTeleBot):
    """Attempt to acquire the desired plan"""
    user = data["user"]
    plan_id = update.data.split("/")[1]
    plan = await Plan.objects.get_basic().filter(pk=plan_id).aget()
    payment = await Payment.objects.new_from_bot(plan=plan, user=user)
    identified_price_task = Payment.objects.get_identified_rial_price(payment.pk)
    ctc_gate_task = payment.get_related_ctc_gate()
    identified_price, ctc_gate = await asyncio.gather(identified_price_task, ctc_gate_task)
    if ctc_gate is None:
        await bot.send_message(
            chat_id=update.message.chat.id,
            text=_("هیچ پذیرنده ای در دسترس نیست"),
        )
        return
    paid_buttom_txt = _("پرداخت کردم")
    text = get_template("seller/pay_off_text.html").render(
        {"identified_price": identified_price, "ctc_gate": ctc_gate, "paid_buttom_txt": paid_buttom_txt}
    )
    keyboard = [
        [
            InlineKeyboardButton(paid_buttom_txt, callback_data=f"check_payment/{payment.pk}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await bot.edit_message_text(
        chat_id=update.message.chat.id,
        message_id=update.message.message_id,
        text=text,
        parse_mode="html",
        reply_markup=reply_markup,
    )


async def check_payment(update: CallbackQuery, data: DataType, bot: AsyncTeleBot):
    """
    The callback in which user says they paid the payment
    """
    user = data["user"]
    payment_id = update.data.split("/")[1]
    payment = await Payment.objects.aget(pk=payment_id, user=user)
    await sync_to_async(payment.pend_admin)(
        update.from_user.username, user_chat_id=update.message.chat.id, user_message_id=update.message.message_id
    )
    await payment.asave()


async def deliver_payment(update: CallbackQuery, data: DataType, bot: AsyncTeleBot):
    """
    The callback when admin sees the sms
    """
    user = data["user"]
    payment_id = update.data.split("/")[1]
    payment = await Payment.objects.aget(pk=payment_id)
    await sync_to_async(payment.set_done)(
        user, user_chat_id=update.message.chat.id, user_message_id=update.message.message_id
    )
    await payment.asave()


async def dont_deliver_payment_yet(update: CallbackQuery, data: DataType, bot: AsyncTeleBot):
    """
    The callback when admin does not see the sms
    """
    user = data["user"]
    payment_id = update.data.split("/")[1]
    payment = await Payment.objects.aget(pk=payment_id)
    await sync_to_async(payment.reject_by_admin)(
        user, user_chat_id=update.message.chat.id, user_message_id=update.message.message_id
    )
    await payment.asave()
