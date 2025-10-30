from __future__ import annotations
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
import logging

from langchain_groq import ChatGroq
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langchain_core.chat_history import InMemoryChatMessageHistory

from .config import PluginConfig

logger = logging.getLogger("FPC.AIAssistant.AIManager")


class AIProvider(ABC):
    @abstractmethod
    def generate_response(self, messages: List[BaseMessage]) -> Optional[str]:
        pass


class GroqProvider(AIProvider):
    def __init__(self, api_key: str):
        self._client = ChatGroq(
            api_key=api_key,
            model_name="groq/compound",
            temperature=0.7
        )

    def generate_response(self, messages: List[BaseMessage]) -> Optional[str]:
        try:
            response = self._client.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"Groq generation error: {e}")
            return None


class MistralProvider(AIProvider):
    def __init__(self, api_key: str):
        self._client = ChatMistralAI(
            api_key=api_key,
            model="mistral-small-2506",
            temperature=0.7
        )

    def generate_response(self, messages: List[BaseMessage]) -> Optional[str]:
        try:
            response = self._client.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"Mistral generation error: {e}")
            return None


class AIManager:
    def __init__(self, config: PluginConfig):
        self._config = config
        self._providers: Dict[str, Optional[AIProvider]] = {
            "groq": None,
            "mistral": None
        }
        self._histories: Dict[int, InMemoryChatMessageHistory] = {}
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        if self._config.groq_api_key:
            try:
                self._providers["groq"] = GroqProvider(self._config.groq_api_key)
                logger.info("Groq provider initialized")
            except Exception as e:
                logger.error(f"Failed to init Groq: {e}")

        if self._config.mistral_api_key:
            try:
                self._providers["mistral"] = MistralProvider(self._config.mistral_api_key)
                logger.info("Mistral provider initialized")
            except Exception as e:
                logger.error(f"Failed to init Mistral: {e}")

    def _get_provider(self) -> Optional[AIProvider]:
        provider = self._providers.get(self._config.default_provider)
        if provider:
            return provider
        
        for p in self._providers.values():
            if p:
                return p
        return None

    def _get_or_create_history(self, chat_id: int) -> InMemoryChatMessageHistory:
        if chat_id not in self._histories:
            self._histories[chat_id] = InMemoryChatMessageHistory()
        return self._histories[chat_id]

    def _trim_history(self, history: InMemoryChatMessageHistory) -> None:
        messages = history.messages
        if len(messages) > self._config.max_history_length:
            history.clear()
            for msg in messages[-self._config.max_history_length:]:
                history.add_message(msg)

    def generate_response(
        self,
        chat_id: int,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        provider = self._get_provider()
        if not provider:
            logger.warning("No AI provider available")
            return None

        history = self._get_or_create_history(chat_id)
        
        messages: List[BaseMessage] = [SystemMessage(content=self._config.system_prompt)]
        
        if context:
            context_parts = []
            if context.get("title"):
                context_parts.append(f"Товар: {context['title']}")
            if context.get("description"):
                context_parts.append(f"Описание: {context['description']}")
            if context.get("price"):
                context_parts.append(f"Цена: {context['price']}₽")
            
            if context_parts:
                messages.append(SystemMessage(content="\n".join(context_parts)))
        
        messages.extend(history.messages)
        messages.append(HumanMessage(content=user_message))
        
        response_content = provider.generate_response(messages)
        
        if response_content:
            history.add_message(HumanMessage(content=user_message))
            history.add_message(AIMessage(content=response_content))
            self._trim_history(history)
        
        return response_content

    def clear_history(self, chat_id: int) -> None:
        if chat_id in self._histories:
            self._histories[chat_id].clear()
            logger.debug(f"History cleared for chat {chat_id}")