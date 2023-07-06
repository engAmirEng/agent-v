from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as BaseUserManager
from django.db.models import CharField
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
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
