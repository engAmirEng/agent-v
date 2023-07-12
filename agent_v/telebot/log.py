import asyncio
import logging

logger = logging.getLogger(__name__)


class AdminTelebotHandler(logging.Handler):
    def __init__(self, admin_chat_id: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.admin_chat_id = admin_chat_id
        self.is_active = True
        if not self.admin_chat_id:
            self.is_active = False
            logger.warning(f"admin_chat_id is set to {admin_chat_id}, this means the {self} is deactivate")

    def emit(self, record: logging.LogRecord) -> None:
        from agent_v.telebot.apps import async_tb

        if not self.is_active:
            return
        log_message = self.format(record)
        tb = async_tb()
        asyncio.create_task(tb.send_message(chat_id=self.admin_chat_id, text=log_message))
