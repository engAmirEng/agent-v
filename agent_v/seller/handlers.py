import asyncio
import enum
import logging

import jdatetime
from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import get_template
from django.utils.translation import gettext as _
from telebot.async_telebot import AsyncTeleBot
from telebot.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from agent_v.hiddify.utils import get_profile
from agent_v.telebot.models import Profile
from agent_v.telebot.utils import DataType, get_data_from_command
from agent_v.users.models import RepresentativeCode

from ..hiddify.models import HProfile, Platform
from .models import Payment, Plan

User = get_user_model()

news_logger = logging.getLogger("news")


class STATES(str, enum.Enum):
    pass


async def start(update: Message, data: DataType, bot: AsyncTeleBot) -> None:
    user = data["user"]
    if user.is_anonymous:
        news_logger.info(f"new start by {update.from_user.username} with {update.text}")
    code = get_data_from_command(update.text, "start").get("code", None)
    if code:
        await bot.send_message(
            update.chat.id,
            "چند لحظه ...",
        )
        await asyncio.sleep(settings.VALIDATE_DELAY)  # to prevent brute force
        code_obj, reason = await RepresentativeCode.objects.validate_code(code)
        if not code_obj:
            if not user.is_anonymous:
                await bot.send_message(
                    chat_id=update.chat.id,
                    text=f"با این لینک امکان تغییر ندارید، {reason}",
                )
            else:
                await bot.send_message(
                    chat_id=update.chat.id,
                    text=f"با این لینک امکان دسترسی ندارید، {reason}",
                )
            return
        else:
            if not user.is_anonymous:
                await Profile.objects.change_rc_code(user=user, rc_code=code_obj)
                await bot.send_message(
                    chat_id=update.chat.id,
                    text="نوع پلن شما تغییر یافت",
                )
            else:
                profile = await Profile.objects.create_in_start_bot(
                    username=update.from_user.username, bot_user_id=update.from_user.id, repr_code=code
                )
                user = await User.objects.aget(pk=profile.user_id)
    else:
        if not not user.is_anonymous:
            if settings.ALLOW_NEW_UNKNOWN:
                profile = await Profile.objects.create_in_start_bot(
                    username=update.from_user.username, bot_user_id=update.from_user.id
                )
                user = await User.objects.aget(pk=profile.user_id)

            else:
                await bot.send_message(update.chat.id, _("برای عضویت نیاز به لینک عضویت میباشد"))
                return

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


async def profile(update: Message, data: DataType, bot: AsyncTeleBot) -> None:
    user = data["user"]
    profile_data = await get_profile(user)
    if profile_data is None:
        await bot.send_message(update.chat.id, "شما هنوز خریدی از بات انجام نداده اید")
        return
    expiry_jdate = jdatetime.date.fromgregorian(date=profile_data["expiry_date"])

    h_profile = await HProfile.objects.aget(user=user)
    url_getter = h_profile.get_subscriptions_url
    text = get_template("seller/profile_text.html").render(
        {
            "plan_title": profile_data["current_plan"].title,
            "remained_data": profile_data["remained_data"],
            "expiry_time": expiry_jdate,
            "v2rayN": url_getter(Platform.V2RAY_N),
            "V2RAY_N_DLL": settings.V2RAY_N_DLL,
            "v2rayNG": url_getter(Platform.V2RAY_NG),
            "V2RAY_NG_DLL": settings.V2RAY_NG_DLL,
            "FairVPN": url_getter(Platform.FAIR_VPN),
            "FAIR_VPN_DLL": settings.FAIR_VPN_DLL,
        }
    )
    await bot.send_message(update.chat.id, text, parse_mode="html")


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
        {
            "plan_title": plan.title,
            "identified_price": identified_price,
            "ctc_gate": ctc_gate,
            "paid_buttom_txt": paid_buttom_txt,
            "proceed": "ادامه",
        }
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
