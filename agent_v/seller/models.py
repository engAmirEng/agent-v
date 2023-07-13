from datetime import timedelta

from asgiref.sync import async_to_sync
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.humanize.templatetags import humanize
from django.core.validators import MinLengthValidator, integer_validator
from django.db import models
from django.db.models import Exists, OuterRef
from django.template.loader import get_template
from django.utils.translation import gettext as __
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField, transition
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from agent_v.hiddify.models import Platform
from agent_v.hiddify.utils import charge_account, create_new_account
from agent_v.seller.utils import PlanType
from agent_v.telebot.models import Profile
from config import settings

User = get_user_model()


class PlanManager(models.QuerySet):
    async def get_for_user(self, user):
        from agent_v.users.models import RepresentativeCode

        plan_type = PlanType.DEFAULT
        rc = await RepresentativeCode.objects.filter(used_by=user).order_by("pk").alast()
        if rc is not None:
            plan_type = rc.plan_type
        one_time_payments = Payment.objects.filter(
            user=user, plan__is_one_time=True, status=Payment.Status.DONE, plan_id=OuterRef("pk")
        )
        return self.filter(is_active=True, plan_type=plan_type).filter(~Exists(one_time_payments))


class Plan(models.Model):
    objects = PlanManager.as_manager()

    plan_type = models.CharField(max_length=15, choices=PlanType.choices, default=PlanType.DEFAULT)
    price = models.PositiveIntegerField(verbose_name=_("قیمت (تومان)"))
    duration = models.PositiveBigIntegerField(verbose_name=_("مدت (ثانیه)"))
    volume = models.PositiveIntegerField(verbose_name=_("حجم (گیگابایت)"))
    is_active = models.BooleanField(default=True)
    is_one_time = models.BooleanField(default=False)

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

    plan = models.ForeignKey("Plan", on_delete=models.PROTECT, verbose_name=_("پلن"), related_name="plan_payments")
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
    def pend_admin(self, user_bot_username: str, user_chat_id: int, user_message_id: int):
        """
        Contains side effects like notifying users, etc.
        The return value will be discarded.
        """
        from agent_v.telebot.apps import async_tb

        bot = async_tb()

        ctc_gate = async_to_sync(self.get_related_ctc_gate)()
        identified_price = async_to_sync(Payment.objects.get_identified_rial_price)(self.pk)
        text = get_template("seller/request_admin_check_text.html").render(
            {"user_username": user_bot_username, "identified_price": identified_price}
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
            chat_id=user_chat_id,
            message_id=user_message_id,
        )

    @transition(field=status, source=[Status.PENDING_ADMIN, Status.ADMIN_REJECTED], target=Status.DONE.value)
    def set_done(self, user, user_chat_id: int, user_message_id: int):
        from agent_v.telebot.apps import async_tb

        bot = async_tb()

        ctc_gate = async_to_sync(self.get_related_ctc_gate)()
        assert ctc_gate.admin_id == user.pk
        async_to_sync(Payment.deliver)(self.pk)
        full_fetched_self = Payment.objects.select_related("user__user_botprofile", "user__user_hprofile", "plan").get(
            pk=self.pk
        )
        url_getter = full_fetched_self.user.user_hprofile.get_subscriptions_url
        text = get_template("seller/deliver_text.html").render(
            {
                "v2rayN": url_getter(Platform.V2RAY_N),
                "V2RAY_N_DLL": settings.V2RAY_N_DLL,
                "v2rayNG": url_getter(Platform.V2RAY_NG),
                "V2RAY_NG_DLL": settings.V2RAY_NG_DLL,
                "FairVPN": url_getter(Platform.FAIR_VPN),
                "FAIR_VPN_DLL": settings.FAIR_VPN_DLL,
                "plan_title": full_fetched_self.plan.title,
            }
        )
        async_to_sync(bot.send_message)(
            chat_id=full_fetched_self.user.user_botprofile.bot_user_id, text=text, parse_mode="html"
        )
        async_to_sync(bot.edit_message_text)("اوکی شد", chat_id=user_chat_id, message_id=user_message_id)

    @transition(field=status, source=[Status.PENDING_ADMIN], target=Status.ADMIN_REJECTED.value)
    def reject_by_admin(self, user, user_chat_id: int, user_message_id: int):
        from agent_v.telebot.apps import async_tb

        bot = async_tb()

        ctc_gate = async_to_sync(self.get_related_ctc_gate)()
        assert ctc_gate.admin_id == user.pk
        async_to_sync(bot.send_message)(chat_id=self.user.user_botprofile.bot_user_id, text="ما که پولی ندیدیم")
        keyboard = [
            [
                InlineKeyboardButton(__("اوا، الان اومد"), callback_data=f"deliver_payment/{self.pk}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        async_to_sync(bot.edit_message_text)(
            "بش گفتم", chat_id=user_chat_id, message_id=user_message_id, reply_markup=reply_markup
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
