from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from agent_v.seller.models import Payment, Plan
from agent_v.telebot.models import Profile
from agent_v.telebot.utils import require_user

User = get_user_model()


@require_user
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, /, user: User) -> None:
    if user.is_anonymous:
        _ = await Profile.objects.create_in_start_bot(
            username=update.effective_user.username, bot_user_id=update.effective_user.id
        )

    plans = Plan.objects.get_basic()
    plans_buttons = [InlineKeyboardButton(i.title, callback_data=f"get_plan/{i.pk}") async for i in plans]
    reply_markup = InlineKeyboardMarkup.from_column(plans_buttons)
    await update.message.reply_text("یکی از پلن ها را انتخاب نمایید", reply_markup=reply_markup)


@require_user
async def get_plan(update: Update, context: ContextTypes.DEFAULT_TYPE, /, user: User):
    """Attempt to acquire the desired plan"""
    query = update.callback_query
    plan_id = query.data.split("/")[1]
    plan = await Plan.objects.get_basic().filter(pk=plan_id).aget()
    payment = await Payment.objects.new_from_bot(plan=plan, user=user)
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton(_("پرداخت کردم"), callback_data=f"check_payment/{payment.pk}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=_("پرداخت کنید سپس پرداخت کردم را یزنید"), reply_markup=reply_markup)


async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass
