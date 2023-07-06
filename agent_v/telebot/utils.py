import functools

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from telegram import Update
from telegram.ext import ContextTypes

User = get_user_model()


def require_user(func):
    """
    A decorator for handlers that passes user as a keyword argument to them
    """

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user = await User.objects.get_by_user_bot_id(update.effective_user.id)
        except User.DoesNotExist:
            user = AnonymousUser
        return await func(update, context, user=user)

    return wrapper
