from datetime import timedelta

from django.contrib.humanize.templatetags import humanize
from django.db import models
from django.utils.translation import gettext_lazy as _

from agent_v.hiddify.utils import charge_account, create_new_account
from config import settings


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
