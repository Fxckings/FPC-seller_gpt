from __future__ import annotations
from typing import TYPE_CHECKING, Optional
import logging

if TYPE_CHECKING:
    from cardinal import Cardinal

from FunPayAPI.updater.events import NewMessageEvent

from plugins.ai_assistant.core.config import PluginConfig
from plugins.ai_assistant.core.ai_manager import AIManager
from plugins.ai_assistant.core.message_processor import MessageProcessor
from plugins.ai_assistant.ui.telegram_handler import TelegramUIHandler
from plugins.ai_assistant.utils.constants import PluginMetadata

logger = logging.getLogger("FPC.AIAssistant")

NAME = PluginMetadata.NAME
VERSION = PluginMetadata.VERSION
DESCRIPTION = PluginMetadata.DESCRIPTION
CREDITS = PluginMetadata.CREDITS
UUID = PluginMetadata.UUID
SETTINGS_PAGE = True


class AIAssistantPlugin:
    def __init__(self, cardinal: Cardinal):
        self._cardinal = cardinal
        self._config = PluginConfig.load()
        self._ai_manager = AIManager(self._config)
        self._message_processor = MessageProcessor(
            cardinal=cardinal,
            ai_manager=self._ai_manager,
            config=self._config
        )
        self._telegram_handler: Optional[TelegramUIHandler] = None
        
        logger.info("AIAssistant plugin initialized")

    def initialize_telegram(self) -> None:
        if self._cardinal.telegram:
            self._telegram_handler = TelegramUIHandler(
                bot=self._cardinal.telegram.bot,
                config=self._config,
                uuid=UUID
            )
            self._telegram_handler.register_handlers(self._cardinal.telegram)
            logger.info("Telegram handlers registered")

    def handle_new_message(self, event: NewMessageEvent) -> None:
        try:
            self._message_processor.process_message(event)
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)


_plugin_instance: Optional[AIAssistantPlugin] = None


def init(cardinal: Cardinal) -> None:
    global _plugin_instance
    _plugin_instance = AIAssistantPlugin(cardinal)
    _plugin_instance.initialize_telegram()


def bind_to_new_message(cardinal: Cardinal, event: NewMessageEvent) -> None:
    if _plugin_instance:
        _plugin_instance.handle_new_message(event)


BIND_TO_PRE_INIT = [init]
BIND_TO_NEW_MESSAGE = [bind_to_new_message]
BIND_TO_DELETE = None