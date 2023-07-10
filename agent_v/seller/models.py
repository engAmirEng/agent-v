from datetime import timedelta

from asgiref.sync import async_to_sync
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.humanize.templatetags import humanize
from django.core.validators import MinLengthValidator, integer_validator
from django.db import models
from django.template.loader import get_template
from django.utils.translation import gettext as __
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField, transition
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from agent_v.hiddify.utils import charge_account, create_new_account
from agent_v.telebot.models import Profile
from config import settings

User = get_user_model()


class PlanManager(models.QuerySet):
    def get_basic(self):
        return self.filter(is_active=True)


class Plan(models.Model):
    objects = PlanManager.as_manager()

    price = models.PositiveIntegerField(verbose_name=_("قیمت (تومان)"))
    duration = models.PositiveBigIntegerField(verbose_name=_("مدت (ثانیه)"))
    volume = models.PositiveIntegerField(verbose_name=_("حجم (گیگابایت)"))
    is_active = models.BooleanField(default=True)

    @property
    def title(self):
        return "{} گیگابایت {} روزه به قیمت {} تومان".format(
            self.volume, timedelta(seconds=self.duration).days, humanize.intcomma(self.price)
        )


class PaymentManager(models.Manager):
    async def new_from_bot(self, plan: Plan, user):
        payment = self.model()
        payment.user = user
        payment.plan = plan
        payment.status = Payment.Status.PENDING
        await payment.asave()
        return payment

    async def get_identified_rial_price(self, payment_pk):
        """
        Returns the price that the payment_id is appended to it in Rial
        """
        payment = await self.model.objects.select_related("plan").aget(pk=payment_pk)
        pk = str(payment.pk)
        rpk = pk[::-1]
        rial = str(payment.plan.price)
        rrial = rial[::-1]
        rres = ""
        for i, v in enumerate(rrial):
            if i + 1 > len(pk):
                rres += v
                continue
            rres += rpk[i]
        res = rres[::-1]
        return res + "0"


class Payment(models.Model):
    objects = PaymentManager()

    class Status(models.TextChoices):
        PENDING = "PE", _("انتظار برای پرداخت")
        PENDING_ADMIN = "PEA", _("انتظار برای تایید ادمین")
        ADMIN_REJECTED = "AR", _("رد توسط ادمین")
        DONE = "DO", _("انجام شده")

    plan = models.ForeignKey("Plan", on_delete=models.PROTECT, verbose_name=_("پلن"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name=_("کاربر"))
    status = FSMField(max_length=4, choices=Status.choices, verbose_name=_("وضعیت"))

    @classmethod
    async def deliver(cls, pk) -> bool:
        """
        Delivers the payment
        """
        payment = await cls.objects.select_related("user__user_hprofile", "plan").aget(pk=pk)
        days = timedelta(seconds=payment.plan.duration).days
        volume = payment.plan.volume
        comment = str(payment)
        try:
            hiddi_profile = payment.user.user_hprofile
        except User.user_hprofile.RelatedObjectDoesNotExist:
            await create_new_account(
                user=payment.user,
                days=days,
                volume=volume,
                comment=comment,
            )
            return True
        else:
            await charge_account(hiddi_id=hiddi_profile.hiddi_id, days=days, volume=volume, comment=comment)
            return False

    @transition(field=status, source=[Status.PENDING], target=Status.PENDING_ADMIN.value)
    def pend_admin(self, user_message: Message):
        """
        Contains side effects like notifying users, etc.
        The return value will be discarded.
        """
        from agent_v.telebot.management.commands.telepoll import async_tb

        bot = async_tb()

        ctc_gate = async_to_sync(self.get_related_ctc_gate)()
        identified_price = async_to_sync(Payment.objects.get_identified_rial_price)(self.pk)
        text = get_template("seller/request_admin_check_text.html").render(
            {"user_username": user_message.from_user.username, "identified_price": identified_price}
        )
        admin_profile = Profile.objects.get(user__user_ctcgates__pk=ctc_gate.pk)
        admin_chat_id = admin_profile.bot_user_id
        keyboard = [
            [
                InlineKeyboardButton(__("آره"), callback_data=f"deliver_payment/{self.pk}"),
                InlineKeyboardButton(__("نه"), callback_data=f"dont_deliver_payment_yet/{self.pk}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        async_to_sync(bot.send_message)(chat_id=admin_chat_id, text=text, parse_mode="html", reply_markup=reply_markup)
        async_to_sync(bot.edit_message_text)(
            __("منتظر بمانید تا تراکنش شما توسط ادمین تایید شود"),
            chat_id=user_message.chat.id,
            message_id=user_message.message_id,
        )

    async def get_related_ctc_gate(self) -> "CardToCardGate":
        """
        Returns the related card to cart gate for the payment
        """
        # TODO
        return await CardToCardGate.objects.get_default()


class CardToCardGateManager(models.Manager):
    async def get_default(self):
        return await self.afirst()


class CardToCardGate(models.Model):
    """
    Admins to check the bank SMS
    """

    objects = CardToCardGateManager()

    card_number = models.CharField(max_length=16, validators=[MinLengthValidator(16), integer_validator])
    cart_info = models.CharField(max_length=255)
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_ctcgates")

    def clean(self) -> None:
        try:
            self.admin.user_botprofile
        except User.user_botprofile.RelatedObjectDoesNotExist:
            raise forms.ValidationError(_("این کاربر در بات پروفایل ندارد"))
