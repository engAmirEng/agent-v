from datetime import timedelta

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.humanize.templatetags import humanize
from django.core.validators import MinLengthValidator, integer_validator
from django.db import models
from django.utils.translation import gettext_lazy as _

from agent_v.hiddify.utils import charge_account, create_new_account
from config import settings

User = get_user_model()


class PlanManager(models.QuerySet):
    def get_basic(self):
        return self.all()


class Plan(models.Model):
    objects = PlanManager.as_manager()

    price = models.PositiveIntegerField(verbose_name=_("قیمت (تومان)"))
    duration = models.PositiveBigIntegerField(verbose_name=_("مدت (ثانیه)"))
    volume = models.PositiveIntegerField(verbose_name=_("حجم (گیگابایت)"))

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
        DONE = "DO", _("انجام شده")

    plan = models.ForeignKey("Plan", on_delete=models.PROTECT, verbose_name=_("پلن"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name=_("کاربر"))
    status = models.CharField(max_length=2, choices=Status.choices, verbose_name=_("وضعیت"))

    @classmethod
    async def deliver(cls, pk):
        """
        Delivers the payment
        """
        payment = await cls.objects.select_related("user__user_hprofile", "plan").aget(pk=pk)
        hiddi_profile = payment.user.user_hprofile
        days = timedelta(seconds=payment.plan.duration).days
        volume = payment.plan.volume
        comment = str(payment)
        if not hiddi_profile:
            await create_new_account(
                user=payment.user,
                days=days,
                volume=volume,
                comment=comment,
            )
            return
        await charge_account(hiddi_id=hiddi_profile.hiddi_id, days=days, volume=volume, comment=comment)

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
