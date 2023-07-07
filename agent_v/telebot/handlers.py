from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message


async def hello(update: Message, data, bot: AsyncTeleBot) -> None:
    await update.message.reply_text(f"Hello {update.effective_user.first_name}")
