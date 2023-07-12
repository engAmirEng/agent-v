import logging

from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message

logger = logging.getLogger(__name__)


async def hello(update: Message, data, bot: AsyncTeleBot) -> None:
    await update.message.reply_text(f"Hello {update.effective_user.first_name}")


async def log_error(update: Message, data, bot: AsyncTeleBot) -> None:
    logger.error("error handler")
