from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = "name_goes_here.users"
    verbose_name = _("Users")

    def ready(self):
        try:
            import name_goes_here.users.signals  # noqa: F401
        except ImportError:
            pass
