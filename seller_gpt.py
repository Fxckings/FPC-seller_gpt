from __future__ import annotations

import requests
from typing import TYPE_CHECKING, Optional, Tuple, Dict, Union, List
from cardinal import Cardinal # type: ignore

if TYPE_CHECKING:
    from cardinal import Cardinal # type: ignore

from FunPayAPI.updater.events import NewMessageEvent # type: ignore
from FunPayAPI.types import MessageTypes # type: ignore
import logging
from os.path import exists
import telebot # type: ignore
import json
import os, re 
from telebot.types import InlineKeyboardMarkup as K, InlineKeyboardButton as B # type: ignore
from urllib.parse import urlparse, parse_qs # type: ignore
from locales.localizer import Localizer # type: ignore
from tg_bot import CBT # type: ignore
from pip._internal.cli.main import main

try:
    from g4f.client import Client # type: ignore
except ImportError:
    main(["install", "g4f"])
    from g4f.client import Client

logger = logging.getLogger("FPC.ChatGPT-Seller")
localizer = Localizer()
_ = localizer.translate

LOGGER_PREFIX = "ChatGPT-Seller"
logger.info(f"{LOGGER_PREFIX} Активен")

NAME = "ChatGPT-Seller"
VERSION = "0.0.8"
DESCRIPTION = """
Плагин, чтобы чат-гпт отвечал за вас, так-как вы можете быть заняты хз:)
_CHANGE LOG_

0.0.8 - sigma update
"""
CREDITS = "@cloudecode"
UUID = "a707de90-d0b5-4fc6-8c42-83b3e0506c73"
SETTINGS_PAGE = True

# Константы для иконок
CHECK_MARK = "✅"
CROSS_MARK = "❌"
BELL = "🔔"
NO_BELL = "🔕"

SETTINGS = {
    "api_key": "",
    "send_response": True,
    "black_list_handle": True,
    "prompt": """
Ты - заместитель продавца на сайте игровых ценностей FunPay. Ты являешься помошником одного из тысячи продавцов.

Твои задачи:

Кратко и чётко отвечать на вопросы покупателей на русском языке
Помогать с выбором товаров
Решать проблемы с заказами
Объяснять правила и механики работы сайта
Не рекламировать и не упоминать другие торговые площадки
Честно признавать, если чего-то не знаю
Соблюдать вежливость и профессионализм
Защищать интересы как покупателей, так и продавцов

"""
}

BAD_WORDS = {
    'ggfunpay',
    'zelenka',
    'зеленка',
    'порно',
    'playerok',
    'плеерок'
}

CBT_SWITCH = "CBTSWITCH"
CBT_PROMPT_CHANGE = "NEW_PROMPT"
CBT_PROMPT_EDITED = "PROMPT_EDITED"
CBT_API_CHANGE = "NEW_API_GROQ"
CBT_API_EDITED = "GROQ_API_EDITED"
CHECK_UPDATES = "CHECK_NEW_VERVION"

lot_cache: Dict[int, Dict[str, Optional[str]]] = {}

def cache_lot_info(chat_id: int, ru_full_lot_info: Optional[str], ru_title_lot_info: Optional[str], price_of_lot: Optional[str]):
    try:
        lot_cache[chat_id] = {
            "ru_full_lot_info": ru_full_lot_info,
            "ru_title_lot_info": ru_title_lot_info,
            "price_of_lot": price_of_lot
        }
    except Exception as e:
        logger.error(e)

def get_latest_release_info(github_repo: str) -> Optional[dict]:
    try:
        response = requests.get(f"https://api.github.com/repos/{github_repo}/releases/latest")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to get the latest release info: {e}")
        return None

def download_file_from_github(download_url: str, file_path: str) -> bool:
    try:
        with requests.get(download_url, stream=True) as response:
            response.raise_for_status()
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        logger.info(f"File successfully downloaded and saved to: {file_path}")
        return True
    except requests.RequestException as e:
        logger.error(f"Error downloading file: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def check_and_update_package(github_repo: str, file_name: str) -> str:
    release_info = get_latest_release_assets(github_repo)
    if not release_info:
        return "Не удалось получить информацию о последнем релизе."

    latest_version, assets = release_info
    asset = next((a for a in assets if a['name'] == file_name), None)
    if VERSION == latest_version:
        return f"Версия {latest_version} уже установлена. Она является последним релизом."

    if asset:
        base_dir = os.path.dirname(__file__)
        file_path = os.path.join(base_dir, file_name)

        if download_file_from_github(asset['browser_download_url'], file_path):
            return f"Файл обновлен до версии {latest_version}."
        else:
            return "Ошибка при загрузке файла."
    else:
        logger.info(f"Файл {file_name} не найден в последнем релизе.")
        return "Файл не найден в последнем релизе."


def get_latest_release_assets(github_repo: str) -> Optional[Tuple[str, List[dict]]]:
    try:
        response = requests.get(f"https://api.github.com/repos/{github_repo}/releases/latest")
        response.raise_for_status()
        release_info = response.json()
        return release_info['tag_name'], release_info.get('assets', [])
    except requests.RequestException as e:
        logger.error(f"Failed to get the latest release info: {e}")
        return None

def check_if_need_update() -> bool:
    try:
        release_info = get_latest_release_info("alex117815/FPC-seller_gpt")
        return release_info and release_info['tag_name'] > VERSION
    except Exception:
        return False

def get_cached_lot_info(chat_id: int) -> Optional[Dict[str, Optional[str]]]:
    return lot_cache.get(chat_id)

def load_file(file_path: str) -> Union[List, Dict, None]:
    try:
        with open(file_path, 'rb') as f:
            return json.loads(f.read().decode('utf-8'))
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при загрузке данных из файла {file_path}: {e}")
    return None

def log_message_info(c: Cardinal, message) -> bool:
    """
    логирует информацию о сообщении

    :param c: The Cardinal instance.
    :param message: The message to log.
    :return: True if the message was logged successfully, False otherwise.
    """
    try:
        bot_username = c.account.username
        logger.info(f"Автор сообщения: {message.author}, Имя текущего бота: {bot_username}")

        if message.type != MessageTypes.NON_SYSTEM or message.author_id == c.account.id:
            return False

        logger.info(f"Новое сообщение получено: {message.text}")
        return True
    except Exception as e:
        logger.error(e)
        return False

def sanitize_response(response: str) -> str:
    """
    Удалите ненужные символы, ссылки и сообщения из ответа.

    :param response: The original response text.
    :return: The cleaned response text.
    """
    response = re.sub(r'[*\#№%/@$%^&<>[\]]', '', response)
    response = re.sub(r'\b({})\b'.format('|'.join(BAD_WORDS)), '', response)
    response = re.sub(r'(http[s]?://\S+|<br>|<h1>|<h2>|<h3>|<p>|</p>)', '', response)

    return response

RESPONSE_CACHE = {}
def generate_response(messages: list, model: str) -> Optional[str]:
    """
    Генерирует ответ от модели на основе предоставленных сообщений.

    :param messages: Список сообщений для модели.
    :param model: Модель для использования.
    :return: Сгенерированный ответ или None в случае ошибки.
    """
    try:
        key = str((model, tuple(sorted(messages))))
        if key in RESPONSE_CACHE:
            return RESPONSE_CACHE[key]

        response = Client().chat.completions.create(
            model=model,
            messages=messages,
        )
        RESPONSE_CACHE[key] = response.choices[0].message.content
        
        return RESPONSE_CACHE[key]
        
    except Exception as e:
        logger.error(f"Error generating a response with the Groq client: {e}")

    return None

def create_response(chat_id: int, ru_full_lot_info: Optional[str], ru_title_lot_info: Optional[str], 
                    price_of_lot: Optional[str], message_text: str, prompt: str) -> Optional[str]:
    """
    Создает ответ на основе предоставленной информации и кэшированных данных.

    :param chat_id: Идентификатор чата.
    :param ru_full_lot_info: Полная информация о лоте.
    :param ru_title_lot_info: Название лота.
    :param price_of_lot: Цена лота.
    :param message_text: Текст сообщения от пользователя.
    :param prompt: Системное сообщение для генерации ответа.
    :return: Сгенерированный ответ или None в случае ошибки.
    """
    try:
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": "Я могу оплатить данный товар?"},
            {"role": "assistant", "content": f"Да, конечно!"},
            {"role": "user", "content": "Кто ты?"},
            {"role": "assistant", "content": "Я бот, который помогает продавцам отвечать, когда они не в сети."},
        ]

        cached_info = get_cached_lot_info(chat_id)
        if cached_info:
            ru_full_lot_info = cached_info["ru_full_lot_info"]
            ru_title_lot_info = cached_info["ru_title_lot_info"]
            price_of_lot = cached_info["price_of_lot"]
        else:
            cache_lot_info(chat_id, ru_full_lot_info, ru_title_lot_info, price_of_lot)

        if ru_full_lot_info:
            messages += [
                {"role": "assistant", "content": f"🔍 Название лота: {ru_title_lot_info}"},
                {"role": "assistant", "content": f"📝 Описание лота: {ru_full_lot_info}"},
                {"role": "assistant", "content": f"Цена товара: {price_of_lot}₽"},
                {"role": "user", "content": message_text},
            ]
        else:
            messages += [
                {"role": "user", "content": message_text},
            ]
        response = generate_response(messages, model="gpt-4o-mini")
        sanitized_response = sanitize_response(response)
        return sanitized_response
    except Exception as e:
        logger.error(f"Ошибка при создании ответа для чата {chat_id}: {e}")
        return None

def handle_message(c: Cardinal, chat_id: int, message_text: str) -> None:
    """
    Обрабатывает сообщение и отправляет ответ.

    :param c: Объект Cardinal.
    :param chat_id: Идентификатор чата.
    :param message_text: Текст сообщения от пользователя.
    """
    ru_full_lot_info, ru_title_lot_info, price_of_lot = get_info(c, chat_id)
    response = create_response(chat_id, ru_full_lot_info, ru_title_lot_info, price_of_lot, message_text, SETTINGS["prompt"])

    c.send_message(chat_id, response)

def contains_url(text: str) -> bool:
    """
    Есть ли ссылки в тексте
    """
    return "http" in text or "https" in text

def bind_to_new_message(c: Cardinal, e: NewMessageEvent):
    """
    Обработчик новых сообщений.

    :param c: The Cardinal instance.
    :param e: The NewMessageEvent instance.
    """
    try:
        if SETTINGS["send_response"]:
            if e.message.chat_name in c.blacklist:
                if SETTINGS['black_list_handle'] == False:
                    logger.info(f"{e.message.chat_name} в ЧС!")
                    return

            msg = e.message

            if not log_message_info(c, msg):
                return
            
            msg = msg.text.lower()
            
            if len(msg) < 10 or len(msg.split()) < 2:
                return

            if contains_url(msg):
                return

            handle_message(c, e.message.chat_id, msg)
    except Exception as e:
        logger.error(e)

def parse_lot_id(url: str) -> Optional[str]:
    """
    Парсит идентификатор лота из URL.

    :param url: Строка URL для парсинга.
    :return: Идентификатор лота, если он найден, иначе None.
    """
    try:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        lot_id = query_params.get('id', [None])[0]
        return lot_id
    except Exception as e:
        logger.error(f"Ошибка при разборе URL: {e}")
        return None

def get_lot_information(cardinal, lot_id: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Получает информацию о лоте.

    :param cardinal: Объект cardinal для взаимодействия с API.
    :param lot_id: Идентификатор лота.
    :return: Кортеж, содержащий описание, название и цену лота. Если данные не найдены, возвращаются None.
    """
    lot_data = cardinal.account.get_lot_fields(lot_id)
    if lot_data:
        description = lot_data.get('description_ru')
        title = lot_data.get('title_ru')
        price = lot_data.get('price')
        
        logger.info(f"Название: {title}")
        logger.info(f"Описание: {description}")
        logger.info(f"Цена: {price}")
        
        return description, title, price
    else:
        logger.error(f"Не удалось получить данные лота для lot_id: {lot_id}")
        return None, None, None

def get_info(cardinal, chat_id: int) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Получает информацию о лоте, который просматривает пользователь в чате.

    :param cardinal: Объект cardinal для взаимодействия с API.
    :param chat_id: Идентификатор чата.
    :return: Кортеж, содержащий полную информацию о лоте, название лота и цену. Если данные не найдены, возвращаются None.
    """
    try:
        user_data = cardinal.account.get_chat(chat_id)

        if not user_data:
            logger.error(f"Не удалось получить данные пользователя для chat_id: {chat_id}")
            return None, None, None

        if user_data.get('looking_link'):
            lot_id = parse_lot_id(user_data['looking_link'])
            if lot_id:
                logger.info(f"Пользователь просматривает лот: {lot_id}")
                return get_lot_information(cardinal, lot_id)

        logger.info("Пользователь не просматривает лот")
        return None, None, None
    except Exception as e:
        logger.error(f"Неожиданная ошибка при получении информации: {e}")
        return None, None, None

def init(c: Cardinal):
    tg = c.telegram
    bot = tg.bot

    can_update = check_if_need_update()
    if can_update:
        bot.send_message(c.telegram.authorized_users[0], f'🚨 Внимание!\nДоступно обновление плагина {LOGGER_PREFIX}, перейдите в настройки плагина чтобы обновить его')

    if exists("storage/plugins/GPTseller.json"):
        with open("storage/plugins/GPTseller.json", "r", encoding="UTF-8") as f:
            global SETTINGS
            SETTINGS = json.loads(f.read())

    def save_config():
        with open("storage/plugins/GPTseller.json", "w", encoding="UTF-8") as f:
            global SETTINGS
            f.write(json.dumps(SETTINGS, indent=4, ensure_ascii=False))

    def switch(call: telebot.types.CallbackQuery):
        try:
            setting_key = call.data.split(":")[1]
            if setting_key in SETTINGS:
                SETTINGS[setting_key] = not SETTINGS[setting_key]
                save_config()
                settings(call)
        except Exception as e:
            logger.error(e)

    def settings(call: telebot.types.CallbackQuery) -> None:
        try:
            keyboard = K()
            keyboard.add(B("🚧 Изменить PROMPT", callback_data=CBT_PROMPT_CHANGE))
            keyboard.add(B("🚧 Изменить api_key", callback_data=CBT_API_CHANGE))

            def create_icon_button(label, setting_key, switch_key):
                icon = CHECK_MARK if SETTINGS[setting_key] else CROSS_MARK
                return [
                    B(label, callback_data=f"{CBT_SWITCH}:{switch_key}"),
                    B(icon, callback_data=f"{CBT_SWITCH}:{switch_key}_icon")
                ]

            keyboard.row(*create_icon_button("Включен:", 'send_response', 'send_response'))

            keyboard.row(*create_icon_button("Отвечать ЧСникам:", 'black_list_handle', 'black_list_handle'))

            keyboard.row(B("🔄 Проверить обновления", callback_data=CHECK_UPDATES))

            keyboard.row(B("◀️ Назад", callback_data=f"{CBT.EDIT_PLUGIN}:{UUID}:0"))

            message_text = (
                "⚠️ Здесь вы можете настроить плагин.\n"
                f"🚽 Если че писать сюда: {CREDITS}\n"
            )

            bot.edit_message_text(
                message_text, 
                call.message.chat.id, 
                call.message.id, 
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(e)

    def handle_update(call: telebot.types.CallbackQuery):
        try:
            github_repo = "alex117815/FPC-seller_gpt"
            file_name = "seller_gpt.py"
            update_message = check_and_update_package(github_repo, file_name)
            bot.answer_callback_query(call.id, text=update_message)

            if "обновлен до версии" not in update_message:
                return

            file_path = os.path.abspath(__file__)
            file_path = os.path.join(os.path.dirname(file_path), file_name)

            with open(file_path, 'rb') as file:
                bot.send_chat_action(call.message.chat.id, "upload_document")
                bot.send_document(call.message.chat.id, file, caption="🚀 Обновление успешно завершено.\n/restart чтобы обновление работало.")
        except Exception as e:
            logger.exception("Error in Telegram bot handler")
            bot.answer_callback_query(call.id, text="Произошла ошибка при выполнении хэндлера Telegram бота.")

    def toggle_send_response(call: telebot.types.CallbackQuery):
        try:
            SETTINGS["send_response"] = not SETTINGS.get("send_response", False)
            save_config()
            settings(call)
        except Exception as e:
            logger.error(e)

    def toggle_handle_black_listed_users(call: telebot.types.CallbackQuery):
        try:
            SETTINGS["black_list_handle"] = not SETTINGS.get("black_list_handle", False)
            save_config()
            settings(call)
        except Exception as e:
            logger.error(e)

    def edit_prompt(call: telebot.types.CallbackQuery):
        if call.data != f"{CBT.PLUGIN_SETTINGS}:{UUID}:0":
            msg = bot.send_message(call.message.chat.id, f"Ваш прошлый PROMPT:<code>{SETTINGS['prompt']}</code>\n\nВведите новый промпт:")
            bot.register_next_step_handler(msg, edited_prompt)

    def edited_prompt(message: telebot.types.Message):
        try:
            new_prompt = message.text
            SETTINGS["prompt"] = new_prompt
            save_config()
            tg.clear_state(message.chat.id, message.from_user.id, True)
            keyboard = K()
            keyboard.add(B("◀️ Назад", callback_data=f"{CBT.PLUGIN_SETTINGS}:{UUID}:0"))
            bot.reply_to(message, f"🟢 Новый промпт установлен: <code>{new_prompt}</code>", reply_markup=keyboard)
        except Exception as e:
            bot.delete_message(message.chat.id, message.id)

    def edit_api(call: telebot.types.CallbackQuery):
        if call.data!= f"{CBT.PLUGIN_SETTINGS}:{UUID}:0":
            msg = bot.send_message(call.message.chat.id, f"Введите новый API-KEY:")
            bot.register_next_step_handler(msg, edited_api)

    def edited_api(message: telebot.types.Message):
        try:
            new_api_key = message.text
            SETTINGS["api_key"] = new_api_key
            save_config()
            tg.clear_state(message.chat.id, message.from_user.id, True)
            keyboard = K()
            keyboard.add(B("◀️ Назад", callback_data=f"{CBT.PLUGIN_SETTINGS}:{UUID}:0"))
            bot.reply_to(message, f"🟢 Новый API-KEY установлен: <code>{new_api_key}</code>", reply_markup=keyboard)
        except Exception as e:
            bot.delete_message(message.chat.id, message.id)

    tg.cbq_handler(edit_prompt, lambda c: CBT_PROMPT_CHANGE in c.data)
    tg.msg_handler(edited_prompt, func=lambda m: tg.check_state(m.chat.id, m.from_user.id, f"{CBT_PROMPT_EDITED}"))
    tg.cbq_handler(edit_api, lambda c: CBT_API_CHANGE in c.data)
    tg.msg_handler(edited_api, func=lambda m: tg.check_state(m.chat.id, m.from_user.id, f"{CBT_API_EDITED}"))
    tg.cbq_handler(toggle_send_response, lambda c: f"{CBT_SWITCH}:send_response" in c.data)
    tg.cbq_handler(toggle_handle_black_listed_users, lambda c: f"{CBT_SWITCH}:black_list_handle" in c.data)
    tg.cbq_handler(switch, lambda c: CBT_SWITCH in c.data)
    tg.cbq_handler(settings, lambda c: f"{CBT.PLUGIN_SETTINGS}:{UUID}" in c.data)
    tg.cbq_handler(handle_update, lambda c: CHECK_UPDATES in c.data)

BIND_TO_NEW_MESSAGE = [bind_to_new_message]
BIND_TO_DELETE = None
BIND_TO_PRE_INIT = [init]
