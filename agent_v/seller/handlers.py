import asyncio
import enum

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import get_template
from django.utils.translation import gettext as _
from telebot.async_telebot import AsyncTeleBot
from telebot.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from agent_v.seller.models import Payment, Plan
from agent_v.telebot.models import Profile
from agent_v.telebot.utils import DataType, get_data_from_command
from agent_v.users.models import RepresentativeCode

User = get_user_model()


class STATES(str, enum.Enum):
    pass


async def start(update: Message, data: DataType, bot: AsyncTeleBot) -> None:
    user = data["user"]
    if user.is_anonymous:
        if settings.ALLOW_NEW_UNKNOWN:
            profile = await Profile.objects.create_in_start_bot(
                username=update.from_user.username, bot_user_id=update.from_user.id
            )
        else:
            code = get_data_from_command(update.text, "start").get("code", None)
            if code is None:
                await bot.send_message(update.chat.id, _("برای عضویت نیاز به لینک عضویت میباشد"))
                return
            await bot.send_message(
                update.chat.id,
                "چند لحظه ...",
            )
            await asyncio.sleep(settings.VALIDATE_DELAY)  # to prevent brute force
            code_obj, reason = await RepresentativeCode.objects.validate_code(code)
            if not code_obj:
                await bot.send_message(
                    chat_id=update.chat.id,
                    text=f"با این لینک امکان دسترسی ندارید، {reason}",
                )
                return
            profile = await Profile.objects.create_in_start_bot(
                username=update.from_user.username, bot_user_id=update.from_user.id, repr_code=code
            )
        user = await User.objects.get(pk=profile.user_id)

    plans = await Plan.objects.get_for_user(user=user)
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


async def change_rc_code(update: Message, data: DataType, bot: AsyncTeleBot) -> None:
    user = data["user"]
    if user.is_anonymous:
        return
    code = get_data_from_command(update.text, "change_rc_code").get("code", None)
    if code is None:
        await bot.send_message(update.chat.id, _("کدی دریافت نشد"))
        return
    await bot.send_message(
        update.chat.id,
        "چند لحظه ...",
    )
    await asyncio.sleep(settings.VALIDATE_DELAY)  # to prevent brute force
    code_obj, reason = await RepresentativeCode.objects.validate_code(code)
    if not code_obj:
        await bot.send_message(
            chat_id=update.chat.id,
            text=f"با این لینک امکان تغییر ندارید، {reason}",
        )
        return
    await Profile.objects.change_rc_code(user=user, rc_code=code_obj)
    await bot.send_message(
        chat_id=update.chat.id,
        text="انجام شد",
    )


async def get_plan(update: CallbackQuery, data: DataType, bot: AsyncTeleBot):
    """Attempt to acquire the desired plan"""
    user = data["user"]
    if user.is_anonymous:
        return
    plan_id = update.data.split("/")[1]
    plans = await Plan.objects.get_for_user(user=user)
    plan = await plans.filter(pk=plan_id).aget()
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
    if user.is_anonymous:
        return
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
    if user.is_anonymous:
        return
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
    if user.is_anonymous:
        return
    payment_id = update.data.split("/")[1]
    payment = await Payment.objects.aget(pk=payment_id)
    await sync_to_async(payment.reject_by_admin)(
        user, user_chat_id=update.message.chat.id, user_message_id=update.message.message_id
    )
    await payment.asave()
