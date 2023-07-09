import asyncio
import enum

from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import get_template
from django.utils.translation import gettext as _
from telebot.async_telebot import AsyncTeleBot
from telebot.types import CallbackQuery, ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, Message

from agent_v.hiddify.models import Platform
from agent_v.seller.models import Payment, Plan
from agent_v.telebot.models import Profile
from agent_v.telebot.utils import require_user
from agent_v.users.models import RepresentativeCode

User = get_user_model()


class STATES(str, enum.Enum):
    ENTERING_REPRESENTATIVE_CODE = "entering_representative_code"


@require_user
async def start(update: Message, data, bot: AsyncTeleBot, /, user: User) -> None:
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
    await bot.send_message(
        update.chat.id,
        "یکی از پلن ها را انتخاب نمایید",
        reply_markup=markup,
    )


async def validate_representative_code(update: Message, data, bot: AsyncTeleBot):
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
    await bot.edit_message_text(
        "یکی از پلن ها را انتخاب نمایید",
        chat_id=a_moment_message.chat.id,
        message_id=a_moment_message.message_id,
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
    payment = await Payment.objects.select_related("user__user_botprofile", "user__user_hprofile", "plan").aget(
        pk=payment_id
    )
    ctc_gate = await payment.get_related_ctc_gate()
    assert ctc_gate.admin_id == user.pk
    is_new_created = await Payment.deliver(payment_id)
    if is_new_created:
        payment = await Payment.objects.select_related("user__user_botprofile", "user__user_hprofile", "plan").aget(
            pk=payment_id
        )
    url_getter = payment.user.user_hprofile.get_subscriptions_url
    text = get_template("seller/deliver_text.html").render(
        {
            "v2rayN": url_getter(Platform.V2RAY_N),
            "V2RAY_N_DLL": settings.V2RAY_N_DLL,
            "v2rayNG": url_getter(Platform.V2RAY_NG),
            "V2RAY_NG_DLL": settings.V2RAY_NG_DLL,
            "FairVPN": url_getter(Platform.FAIR_VPN),
            "FAIR_VPN_DLL": settings.FAIR_VPN_DLL,
            "plan_title": payment.plan.title,
        }
    )
    await bot.send_message(chat_id=payment.user.user_botprofile.bot_user_id, text=text, parse_mode="html")
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
