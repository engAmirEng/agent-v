import enum
from typing import Optional

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as BaseUserManager
from django.db import models
from django.db.models import CharField, Count, Q, QuerySet
from django.utils.translation import gettext_lazy as _

from agent_v.seller.utils import PlanType


class UserQuerySet(QuerySet):
    def an_successful_payment_count(self):
        """
        annotates with successful payment count related to the user
        """
        from agent_v.seller.models import Payment

        return self.annotate(successful_payment_count=Count("payment", filter=Q(payment__status=Payment.Status.DONE)))


class UserManager(BaseUserManager):
    def get_queryset(self):
        return UserQuerySet(self.model, using=self._db)

    async def get_by_user_bot_id(self, user_bot_id: int):
        return await User.objects.aget(user_botprofile__bot_user_id=user_bot_id)


class User(AbstractUser):
    """
    Default custom user model for agent_v.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    objects = UserManager()

    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore
    last_name = None  # type: ignore


class CODE_NOT_VALID_REASON(str, enum.Enum):
    CAPACITY = "capacity"
    NOT_FOUNT = "not_found"
    DEACTIVATED = "deactivated"


class RepresentativeCodeQuerySet(models.QuerySet):
    def an_used_by_count(self):
        return self.annotate(used_by_count=Count("used_by"))

    async def validate_code(self, code: str) -> (Optional["RepresentativeCode"], CODE_NOT_VALID_REASON):
        """
        If a code can be used or not and why
        """
        try:
            code_obj: RepresentativeCode = await self.aget(code=code)
        except RepresentativeCode.DoesNotExist:
            return None, CODE_NOT_VALID_REASON.NOT_FOUNT.value
        if not code_obj.is_active:
            return None, CODE_NOT_VALID_REASON.DEACTIVATED.value
        elif not await code_obj.has_capacity(code_obj.pk):
            return None, CODE_NOT_VALID_REASON.CAPACITY.value
        return code_obj, None

    async def use_for(self, code: str, user):
        """
        Mark a code as used for user
        """
        obj: RepresentativeCode = await self.aget(code=code)
        await obj.used_by.aadd(user)
        await obj.asave()


class RepresentativeCode(models.Model):
    objects = RepresentativeCodeQuerySet.as_manager()

    code = models.CharField(max_length=15, unique=True)
    capacity = models.PositiveSmallIntegerField(default=1)
    plan_type = models.CharField(max_length=15, choices=PlanType.choices, default=PlanType.DEFAULT)
    used_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="user_rcodes", blank=True)
    is_active = models.BooleanField(default=True)
    descriptions = models.TextField()

    @classmethod
    async def has_capacity(cls, pk):
        """
        Left any capacity or not
        """
        obj = await cls.objects.an_used_by_count().aget(pk=pk)
        return obj.capacity - obj.used_by_count > 0
