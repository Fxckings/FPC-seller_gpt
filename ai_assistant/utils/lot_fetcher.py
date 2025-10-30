from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Dict, Any
import logging

if TYPE_CHECKING:
    from cardinal import Cardinal

logger = logging.getLogger("FPC.AIAssistant.LotFetcher")


class LotInfoFetcher:
    def __init__(self, cardinal: Cardinal):
        self._cardinal = cardinal
        self._cache: Dict[int, Dict[str, Any]] = {}

    def _parse_lot_id(self, url: str) -> Optional[str]:
        if "?id=" in url:
            return url.split("?id=")[-1]
        return None

    def _fetch_lot_data(self, lot_id: str) -> Optional[Dict[str, Any]]:
        try:
            lot_data = self._cardinal.account.get_lot_fields(lot_id)
            if not lot_data:
                return None

            return {
                "description": getattr(lot_data, "description_ru", None),
                "title": getattr(lot_data, "title_ru", None),
                "price": getattr(lot_data, "price", None)
            }
        except Exception as e:
            logger.error(f"Error fetching lot data: {e}")
            return None

    def get_lot_context(self, chat_id: int) -> Optional[Dict[str, Any]]:
        if chat_id in self._cache:
            return self._cache[chat_id]

        try:
            user_data = self._cardinal.account.get_chat(chat_id)
            if not user_data or not hasattr(user_data, "looking_link"):
                return None

            if not user_data.looking_link:
                return None

            lot_id = self._parse_lot_id(user_data.looking_link)
            if not lot_id:
                return None

            lot_data = self._fetch_lot_data(lot_id)
            if lot_data:
                self._cache[chat_id] = lot_data
                logger.debug(f"Lot context cached for chat {chat_id}")
            
            return lot_data

        except Exception as e:
            logger.error(f"Error getting lot context: {e}")
            return None

    def clear_cache(self, chat_id: Optional[int] = None) -> None:
        if chat_id:
            self._cache.pop(chat_id, None)
        else:
            self._cache.clear()