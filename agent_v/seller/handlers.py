import asyncio

from django.contrib.auth import get_user_model
from django.template.loader import get_template
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


async def check_payment(update: CallbackQuery, data, bot: AsyncTeleBot):
    """
    The callback in which user says they paid the payment
    """
    payment_id = update.data.split("/")[1]
    payment = await Payment.objects.aget(pk=payment_id)
    ctc_gate_task = payment.get_related_ctc_gate()
    identified_price_task = Payment.objects.get_identified_rial_price(payment.pk)
    ctc_gate, identified_price = await asyncio.gather(ctc_gate_task, identified_price_task)
    text = get_template("seller/request_admin_check_text.html").render(
        {"user_username": update.from_user.username, "identified_price": identified_price}
    )
    admin_profile = await Profile.objects.aget(user__user_ctcgates__pk=ctc_gate.pk)
    admin_chat_id = admin_profile.bot_user_id
    keyboard = [
        [
            InlineKeyboardButton(_("آره"), callback_data=f"deliver_payment/{payment.pk}"),
            InlineKeyboardButton(_("نه"), callback_data=f"dont_deliver_payment_yet/{payment.pk}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await bot.send_message(chat_id=admin_chat_id, text=text, parse_mode="html", reply_markup=reply_markup)
    await bot.edit_message_text(
        "منتظر بمانید تا تراکنش شما توسط ادمین تایید شود",
        chat_id=update.message.chat.id,
        message_id=update.message.message_id,
    )


@require_user
async def deliver_payment(update: CallbackQuery, data, bot: AsyncTeleBot, /, user: User):
    """
    The callback when admin sees the sms
    """
    payment_id = update.data.split("/")[1]
    payment = await Payment.objects.select_related("user__user_botprofile").aget(pk=payment_id)
    ctc_gate = await payment.get_related_ctc_gate()
    assert ctc_gate.admin_id == user.pk
    await Payment.deliver(payment_id)
    await bot.send_message(chat_id=payment.user.user_botprofile.bot_user_id, text="این تحویل شما")
    await bot.edit_message_text("اوکی شد", chat_id=update.message.chat.id, message_id=update.message.message_id)


@require_user
async def dont_deliver_payment_yet(update: CallbackQuery, data, bot: AsyncTeleBot, /, user: User):
    """
    The callback when admin does not see the sms
    """
    payment_id = update.data.split("/")[1]
    payment = await Payment.objects.select_related("user__user_botprofile").aget(pk=payment_id)
    ctc_gate = await payment.get_related_ctc_gate()
    assert ctc_gate.admin_id == user.pk
    await bot.send_message(chat_id=payment.user.user_botprofile.bot_user_id, text="ما که پولی ندیدیم")
    keyboard = [
        [
            InlineKeyboardButton(_("اوا، الان اومد"), callback_data=f"deliver_payment/{payment.pk}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await bot.edit_message_text(
        "بش گفتم", chat_id=update.message.chat.id, message_id=update.message.message_id, reply_markup=reply_markup
    )
