from dataclasses import dataclass


@dataclass(frozen=True)
class PluginMetadata:
    NAME: str = "AIAssistant"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = (
        "AI-ассистент для автоматических ответов покупателям.\n"
        "Использует LangChain с Groq/Mistral.\n"
        "Команда: !вопрос <текст>\n\n"
        "v1.0.0 - Полный рефакторинг с LangChain"
    )
    CREDITS: str = "@cloudecode"
    UUID: str = "a707de90-d0b5-4fc6-8c42-83b3e0506c73"


@dataclass(frozen=True)
class UIConstants:
    CHECK_MARK: str = "✅"
    CROSS_MARK: str = "❌"
    BELL: str = "🔔"
    NO_BELL: str = "🔕"


@dataclass(frozen=True)
class CallbackData:
    SWITCH: str = "AI_SWITCH"
    EDIT_PROMPT: str = "AI_PROMPT_EDIT"
    EDIT_PREFIX: str = "AI_PREFIX_EDIT"
    PROVIDER: str = "AI_PROVIDER"
    CLEAR_HISTORY: str = "AI_CLEAR_HIST"