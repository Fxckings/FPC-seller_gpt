from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any
from pathlib import Path
import json
import logging

logger = logging.getLogger("FPC.AIAssistant.Config")


@dataclass
class PluginConfig:
    enabled: bool = True
    handle_blacklisted: bool = False
    command_prefix: str = "!вопрос"
    mistral_api_key: str = ""
    groq_api_key: str = ""
    default_provider: str = "groq"
    system_prompt: str = field(default_factory=lambda: (
        "Ты - помощник продавца на FunPay. "
        "Отвечай кратко и профессионально на русском языке. "
        "Помогай с выбором товаров и решением проблем с заказами. "
        "Соблюдай вежливость. Не упоминай другие площадки."
    ))
    max_history_length: int = 10
    cache_enabled: bool = True
    
    _config_path: Path = field(default=Path("storage/plugins/ai_assistant.json"), init=False)

    @classmethod
    def load(cls) -> PluginConfig:
        config_path = Path("storage/plugins/ai_assistant.json")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    instance = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
                    instance._config_path = config_path
                    logger.info("Configuration loaded")
                    return instance
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        
        instance = cls()
        instance._config_path = config_path
        instance.save()
        return instance

    def save(self) -> None:
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            data = {k: v for k, v in asdict(self).items() if not k.startswith("_")}
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.debug("Configuration saved")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def update(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.save()