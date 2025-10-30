from __future__ import annotations
from typing import TYPE_CHECKING, Callable
import logging

if TYPE_CHECKING:
    from telebot import TeleBot
    from telebot.types import CallbackQuery, Message
    from tg_bot import TgBot

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from ..core.config import PluginConfig
from ..utils.constants import UIConstants, CallbackData
from tg_bot import CBT

logger = logging.getLogger("FPC.AIAssistant.TelegramUI")


class TelegramUIHandler:
    def __init__(self, bot: TeleBot, config: PluginConfig, uuid: str):
        self._bot = bot
        self._config = config
        self._uuid = uuid
        self._awaiting_prompt: set[int] = set()
        self._awaiting_prefix: set[int] = set()

    def register_handlers(self, tg_bot: TgBot) -> None:
        tg_bot.cbq_handler(self._show_settings, lambda c: f"{CBT.PLUGIN_SETTINGS}:{self._uuid}" in c.data)
        tg_bot.cbq_handler(self._toggle_setting, lambda c: CallbackData.SWITCH in c.data)
        tg_bot.cbq_handler(self._request_prompt, lambda c: CallbackData.EDIT_PROMPT in c.data)
        tg_bot.cbq_handler(self._request_prefix, lambda c: CallbackData.EDIT_PREFIX in c.data)
        tg_bot.cbq_handler(self._change_provider, lambda c: CallbackData.PROVIDER in c.data)
        
        tg_bot.msg_handler(self._handle_prompt_input, func=lambda m: m.from_user.id in self._awaiting_prompt)
        tg_bot.msg_handler(self._handle_prefix_input, func=lambda m: m.from_user.id in self._awaiting_prefix)

    def _show_settings(self, call: CallbackQuery) -> None:
        try:
            kb = InlineKeyboardMarkup(row_width=2)
            
            kb.add(
                InlineKeyboardButton(
                    "Включен:" if self._config.enabled else "Выключен:",
                    callback_data=f"{CallbackData.SWITCH}:enabled"
                ),
                InlineKeyboardButton(
                    UIConstants.CHECK_MARK if self._config.enabled else UIConstants.CROSS_MARK,
                    callback_data=f"{CallbackData.SWITCH}:enabled"
                )
            )
            
            kb.add(
                InlineKeyboardButton(
                    "Отвечать ЧС:",
                    callback_data=f"{CallbackData.SWITCH}:handle_blacklisted"
                ),
                InlineKeyboardButton(
                    UIConstants.CHECK_MARK if self._config.handle_blacklisted else UIConstants.CROSS_MARK,
                    callback_data=f"{CallbackData.SWITCH}:handle_blacklisted"
                )
            )
            
            kb.add(InlineKeyboardButton("Изменить системный промпт", callback_data=CallbackData.EDIT_PROMPT))
            kb.add(InlineKeyboardButton("Изменить команду", callback_data=CallbackData.EDIT_PREFIX))
            
            provider_text = f"Провайдер: {self._config.default_provider}"
            kb.add(InlineKeyboardButton(provider_text, callback_data=CallbackData.PROVIDER))
            
            kb.add(InlineKeyboardButton("◀️ Назад", callback_data=f"{CBT.EDIT_PLUGIN}:{self._uuid}:0"))
            
            text = (
                f"⚙️ Настройки AI-ассистента\n\n"
                f"Команда: <code>{self._config.command_prefix}</code>\n"
                f"Провайдер: {self._config.default_provider}\n"
                f"История: {self._config.max_history_length} сообщений"
            )
            
            self._bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.id,
                reply_markup=kb,
                parse_mode="HTML"
            )
            self._bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"Error showing settings: {e}")

    def _toggle_setting(self, call: CallbackQuery) -> None:
        try:
            setting = call.data.split(":")[1]
            current = getattr(self._config, setting, None)
            if current is not None:
                self._config.update(**{setting: not current})
                self._show_settings(call)
        except Exception as e:
            logger.error(f"Error toggling setting: {e}")

    def _request_prompt(self, call: CallbackQuery) -> None:
        try:
            self._awaiting_prompt.add(call.from_user.id)
            text = (
                f"Текущий промпт:\n<code>{self._config.system_prompt}</code>\n\n"
                "Введите новый промпт:"
            )
            self._bot.send_message(call.message.chat.id, text, parse_mode="HTML")
            self._bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"Error requesting prompt: {e}")

    def _handle_prompt_input(self, message: Message) -> None:
        try:
            self._awaiting_prompt.discard(message.from_user.id)
            self._config.update(system_prompt=message.text)
            
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("◀️ К настройкам", callback_data=f"{CBT.PLUGIN_SETTINGS}:{self._uuid}:0"))
            
            self._bot.reply_to(
                message,
                f"✅ Промпт обновлен",
                reply_markup=kb
            )
        except Exception as e:
            logger.error(f"Error handling prompt: {e}")

    def _request_prefix(self, call: CallbackQuery) -> None:
        try:
            self._awaiting_prefix.add(call.from_user.id)
            text = (
                f"Текущая команда: <code>{self._config.command_prefix}</code>\n\n"
                "Введите новую команду (например: !вопрос или !ask):"
            )
            self._bot.send_message(call.message.chat.id, text, parse_mode="HTML")
            self._bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"Error requesting prefix: {e}")

    def _handle_prefix_input(self, message: Message) -> None:
        try:
            self._awaiting_prefix.discard(message.from_user.id)
            self._config.update(command_prefix=message.text.strip())
            
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("◀️ К настройкам", callback_data=f"{CBT.PLUGIN_SETTINGS}:{self._uuid}:0"))
            
            self._bot.reply_to(
                message,
                f"✅ Команда обновлена: <code>{message.text.strip()}</code>",
                reply_markup=kb,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error handling prefix: {e}")

    def _change_provider(self, call: CallbackQuery) -> None:
        try:
            new_provider = "mistral" if self._config.default_provider == "groq" else "groq"
            self._config.update(default_provider=new_provider)
            self._show_settings(call)
            self._bot.answer_callback_query(call.id, f"Провайдер изменен на {new_provider}")
        except Exception as e:
            logger.error(f"Error changing provider: {e}")