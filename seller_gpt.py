import subprocess
import sys, requests
import importlib

# Функция для установки пакета с помощью pip
def install_package(package_name: str):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])

# Проверьте, установлен ли g4f, если нет, установите его
try:
    import g4f
except ImportError:
    install_package("g4f")
    install_package("g4f[webdriver]")
    g4f = importlib.import_module("g4f")

# Добавляем проверку и установку для пакета prophet
try:
    import prophet
except ImportError:
    install_package("prophet")
    prophet = importlib.import_module("prophet")

from typing import TYPE_CHECKING, Optional, Tuple, Dict, Union, List
from cardinal import Cardinal
if TYPE_CHECKING:
    from cardinal import Cardinal

from FunPayAPI.updater.events import NewOrderEvent, NewMessageEvent
from FunPayAPI.types import MessageTypes
import logging
import telebot
import json
import os, re
from telebot.types import InlineKeyboardMarkup as K, InlineKeyboardButton as B
from urllib.parse import urlparse, parse_qs
from locales.localizer import Localizer
import g4f
from tg_bot import CBT
import tg_bot.CBT
from g4f.client import Client
from g4f.Provider import Groq, You

logger = logging.getLogger("FPC.GPTPLUG-IN")
localizer = Localizer()
_ = localizer.translate

LOGGER_PREFIX = "GPT-SELLER"
logger.info(f"{LOGGER_PREFIX} ЗАПУСТИЛСЯ!")

NAME = "ChatGPT-Seller"
VERSION = "0.0.5"
DESCRIPTION = """
Плагин, чтобы чат-гпт отвечал за вас, так-как вы можете быть заняты хз:)
_CHANGE LOG_
0.0.2 - настройка в тг
0.0.3 - доработал стабильность
0.0.4 - настройка в тг++
0.0.5 - возможность обновиться через тг
"""
CREDITS = "@zeijuro"
UUID = "a707de90-d0b5-4fc6-8c42-83b3e0506c73"
SETTINGS_PAGE = True

# Константы для иконок
CHECK_MARK = "✅"
CROSS_MARK = "❌"
BELL = "🔔"
NO_BELL = "🔕"

USERNAME = "Tinkovof"

CONFIG_FILE = "storage/plugins/GPTseller.json" #Где находится конфиг
BLACKLIST_FILE = "storage/cache/blacklist.json" #Где находится ЧС

g4f.debug.logging = True
g4f.debug.version_check = True

#Получать с сайта: https://groq.com/
groqapi = "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"

SETTINGS = {
    "groqapi": groqapi,
    "send_response": True,
    "black_list_handle": True,
    "notify_telegram": True,
    "notify_chatid": 0,
    "username": USERNAME,
    "prompt": ""
}

SETTINGS['prompt'] = f"""Ты - заместитель продавца {SETTINGS['username']} на сайте игровых ценностей FunPay.
Помогай покупателям разобраться с товарам и проблемами. Отвечай КРАТНО только на русском языке, пожалуйста, не употребляйте на сайте названия сторонних ресурсов. Если что-то не знаешь так и говори.
"""

#Клиент для ответов
client = Client(api_key=SETTINGS["groqapi"])

#Switch
CBT_SWITCH = "CBTSWITCH"
#Prompt
CBT_PROMPT_CHANGE = "NEW_PROMPT"
CBT_PROMPT_EDITED = "PROMPT_EDITED"
#Name
CBT_NAME_CHANGE = "NAME_CHANGE_CBT"
CBT_NAME_EDITED = "NAME_EDITED_CBT"
#Groq
CBT_API_CHANGE = "NEW_API_GROQ"
CBT_API_EDITED = "GROQ_API_EDITED"
#Check Udated
CHECK_UPDATES = "CHECK_NEW_VERVION"

lot_cache: Dict[int, Dict[str, Optional[str]]] = {}

def save_file(file_path: str, data: Union[List, Dict]) -> None:
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except (IOError, TypeError) as e:
        logger.error(f"Ошибка при сохранении файла {file_path}: {e}")

def log_order_info(order):
    try:
        logger.info(f"Новый заказ получен: {order}")
        logger.info(f"Сумма заказа: {order.amount}")
    except Exception as e:
        logger.error(e)

def order_logger(c: Cardinal, e: NewOrderEvent):
    try:
        order = e.order
        log_order_info(order)
    except Exception as e:
        logger.error(e)

def cache_lot_info(chat_id: int, ru_full_lot_info: Optional[str], ru_title_lot_info: Optional[str], price_of_lot: Optional[str]):
    try:
        lot_cache[chat_id] = {
            "ru_full_lot_info": ru_full_lot_info,
            "ru_title_lot_info": ru_title_lot_info,
            "price_of_lot": price_of_lot
        }
    except Exception as e:
        logger.error(e)

# Функция для установки git, если он отсутствует
def install_git():
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "gitpython"])
        import git
        return True
    except Exception as e:
        logger.error(f"Ошибка установки git: {e}")
        return False

# Функция для проверки и установки обновлений с GitHub
def check_and_update_package(github_repo: str):
    try:
        response = requests.get(f"https://api.github.com/repos/{github_repo}/releases/latest")
        response.raise_for_status()
        latest_version = response.json()['tag_name']
        
        current_version = VERSION # Убедитесь, что переменная VERSION определена
        
        if latest_version != current_version:
            download_file_from_github(github_repo, "seller_gpt.py")
            return f"Файл обновлен до версии {latest_version}."
        else:
            return "Вы используете последнюю версию."
    except Exception as e:
        return f"Не удалось проверить обновления: {str(e)}"

def download_file_from_github(repo_url: str, file_path: str):
    """
    Загружает файл из репозитория GitHub по указанному пути.
    
    :param repo_url: URL репозитория на GitHub.
    :param file_path: Путь к файлу в репозитории.
    :return: None
    """
    # Получаем содержимое файла через API GitHub
    file_url = f"https://raw.githubusercontent.com/{repo_url}/main/{file_path}"
    response = requests.get(file_url)
    
    # Проверяем статус ответа
    response.raise_for_status()
    
    # Сохраняем файл
    with open(file_path, 'wb') as f:
        f.write(response.content)

def get_cached_lot_info(chat_id: int) -> Optional[Dict[str, Optional[str]]]:
    try:
        return lot_cache.get(chat_id)
    except Exception as e:
        logger.error(e)
        return None

def load_file(file_path: str) -> Union[List, Dict, None]:
    if not os.path.exists(file_path):
        logger.warning(f"Файл {file_path} не существует.")
        return None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON в файле {file_path}: {e}")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при загрузке данных из файла {file_path}: {e}")
    return None

def log_message_info(c: Cardinal, message) -> bool:
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

def load_blacklist(file_path: str) -> List[str]:
    """
    Загружает черный список из указанного файла.

    :param file_path: Путь к файлу черного списка.
    :return: Список имен пользователей из черного списка.
    :raises FileNotFoundError: Если файл не найден.
    :raises json.JSONDecodeError: Если произошла ошибка при расшифровке файла.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError as e:
        logger.error(f"Файл с черным списком {file_path} не найдено.")
        raise e
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка при расшифровке файла черного списка {file_path}.")
        raise e

def is_user_blacklisted(username: str) -> bool:
    """
    Проверяет, находится ли пользователь в черном списке.

    :param username: Имя пользователя для проверки.
    :return: True, если пользователь находится в черном списке, иначе False.
    """
    try:
        blacklist = load_blacklist(BLACKLIST_FILE)
        return username in blacklist
    except FileNotFoundError:
        return False
    except json.JSONDecodeError:
        return False
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при проверке черного списка для пользователя {username}: {e}")
        return False

def sanitize_response(response: str) -> str:
    """
    Удаляет нежелательные символы и ссылки из ответа.

    :param response: Исходный текст ответа.
    :return: Очищенный текст ответа.
    """
    unwanted_chars = "*#№%/@$%^&<>[]"
    for char in unwanted_chars:
        response = response.replace(char, "")
    
    # Удаление ссылок из ответа
    response = re.sub(r'http[s]?://\S+', '', response)
    response = re.sub('<br>', '', response)
    
    return response

def generate_response(messages: list, model: str, provider: str) -> Optional[str]:
    """
    Генерирует ответ от модели на основе предоставленных сообщений.

    :param messages: Список сообщений для модели.
    :param model: Модель для использования.
    :param provider: Провайдер модели.
    :return: Сгенерированный ответ или None в случае ошибки.
    """
    try:
        response = client.chat.completions.create(
            model=model,
            provider=provider,
            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Ошибка при генерации ответа с моделью {model} и провайдером {provider}: {e}")
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
            {"role": "system", "content": prompt}
        ]

        # Проверка кэшированных данных
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
                {"role": "user", "content": "Я могу оплатить данный товар?"},
                {"role": "assistant", "content": f"Да, конечно!"},
                {"role": "user", "content": message_text},
            ]
        else:
            messages += [
                {"role": "user", "content": "Я могу оплатить товар?"},
                {"role": "assistant", "content": f"Да, конечно, вы всегда можете!"},
                {"role": "user", "content": message_text},
            ]

        response = generate_response(messages, model="gpt-4", provider=You)
        
        # Попытка генерации ответа с другими настройками при неудаче
        if not response:
            response = generate_response(messages, model="", provider=Groq)
            if not response:
                return None

        sanitized_response = sanitize_response(response)
        return sanitized_response

    except Exception as e:
        logger.error(f"Ошибка при создании ответа для чата {chat_id}: {e}")
        return None

def message_logger(c: Cardinal, e: NewMessageEvent) -> None:
    """
    Логирует и обрабатывает новое сообщение.

    :param c: Объект Cardinal.
    :param e: Событие нового сообщения.
    """
    try:
        message = e.message
        handle_message(c, message.chat_id, message.text)
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")

def handle_message(c: Cardinal, chat_id: int, message_text: str) -> None:
    """
    Обрабатывает сообщение и отправляет ответ.

    :param c: Объект Cardinal.
    :param chat_id: Идентификатор чата.
    :param message_text: Текст сообщения от пользователя.
    """
    ru_full_lot_info, ru_title_lot_info, price_of_lot = get_info(c, chat_id)
    response = create_response(chat_id, ru_full_lot_info, ru_title_lot_info, price_of_lot, message_text, SETTINGS["prompt"])

    if ru_full_lot_info:
        log_lot_info(ru_full_lot_info, ru_title_lot_info, price_of_lot)

    c.send_message(chat_id, response)
    notify_telegram(c, response, message_text)

def log_lot_info(ru_full_lot_info: str, ru_title_lot_info: str, price_of_lot: str) -> None:
    """
    Логирует информацию о лоте.

    :param ru_full_lot_info: Полная информация о лоте.
    :param ru_title_lot_info: Название лота.
    :param price_of_lot: Цена лота.
    """
    logger.info(f"лот {ru_full_lot_info}")
    logger.info(f"опис {ru_title_lot_info}")
    logger.info(f"цена {price_of_lot}")

# Функция для поиска URL в тексте
def contains_url(text: str) -> bool:
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.search(url_pattern, text) is not None

def bind_to_new_message(c: Cardinal, e: NewMessageEvent):
    try:
        if SETTINGS["send_response"]:
            # Проверка на черный список
            if is_user_blacklisted(e.message.chat_name):
                if SETTINGS['black_list_handle'] == False:
                    logger.info(f"{e.message.chat_name} в ЧС!")
                    return

            msg = e.message

            # Проверка на логирование информации о сообщении
            if not log_message_info(c, msg):
                return

            # Игнорирование сообщений, начинающихся с определенных символов или слов
            if msg.text.startswith(("!", "/", "https://", "t.me", "#", "да", "+", "Да", "дА")):
                return
            
            # Проверка на длину сообщения и количество слов
            if len(msg.text) < 10 or len(msg.text.split()) < 2:
                return

            # Добавляем проверку на наличие ссылки в сообщении
            if contains_url(msg.text):
                return

            # Логирование информации о сообщении
            message_logger(c, e)
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

def get_lot_fields(cardinal, lot_id: str) -> Optional[dict]:
    """
    Получает данные лота по идентификатору.

    :param cardinal: Объект cardinal для взаимодействия с API.
    :param lot_id: Идентификатор лота.
    :return: Словарь с данными лота, если данные найдены, иначе None.
    """
    try:
        return cardinal.account.get_lot_fields(lot_id)
    except Exception as e:
        logger.error(f"Неожиданная ошибка при получении данных лота: {e}")
        return None

def get_lot_information(cardinal, lot_id: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Получает информацию о лоте.

    :param cardinal: Объект cardinal для взаимодействия с API.
    :param lot_id: Идентификатор лота.
    :return: Кортеж, содержащий описание, название и цену лота. Если данные не найдены, возвращаются None.
    """
    lot_data = get_lot_fields(cardinal, lot_id)
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

def get_user_chat_data(cardinal, chat_id: int) -> Optional[dict]:
    """
    Получает данные чата пользователя по идентификатору чата.

    :param cardinal: Объект cardinal для взаимодействия с API.
    :param chat_id: Идентификатор чата.
    :return: Словарь с данными чата, если данные найдены, иначе None.
    """
    try:
        return cardinal.account.get_chat(chat_id)
    except Exception as e:
        logger.error(f"Неожиданная ошибка при получении данных чата: {e}")
        return None

def get_info(cardinal, chat_id: int) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Получает информацию о лоте, который просматривает пользователь в чате.

    :param cardinal: Объект cardinal для взаимодействия с API.
    :param chat_id: Идентификатор чата.
    :return: Кортеж, содержащий полную информацию о лоте, название лота и цену. Если данные не найдены, возвращаются None.
    """
    try:
        user_data = get_user_chat_data(cardinal, chat_id)

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

def notify_telegram(c: Cardinal, responce, question):
    bot = c.telegram.bot

    if SETTINGS["notify_telegram"]:
        message = (
            f"<b>Вопрос:</b> <code>{question}<code>\n\n"
            f"<b>Ответ:</b> <code>{responce}</code>"
        )

        bot.send_message(c.telegram.authorized_users[0], f"💻 <b>{LOGGER_PREFIX}</b>\n\n{message}", parse_mode='HTML')

def init(c: Cardinal):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

    global SETTINGS

    save_file(CONFIG_FILE, SETTINGS)

    tg = c.telegram
    bot = tg.bot

    def switch(call: telebot.types.CallbackQuery):
        try:
            setting_key = call.data.split(":")[1]
            if setting_key in SETTINGS:
                SETTINGS[setting_key] = not SETTINGS[setting_key]
                save_config()
                settings(call)
        except Exception as e:
            logger.error(e)

    def save_config():
        try:
            with open(CONFIG_FILE, "w", encoding="UTF-8") as f:
                f.write(json.dumps(SETTINGS, indent=4, ensure_ascii=False))
        except Exception as e:
            logger.error(e)

    def settings(call: telebot.types.CallbackQuery) -> None:
        try:
            keyboard = K()

            # Кнопка быстрого изменения
            keyboard.add(B("🚧 Изменить промпт", callback_data=CBT_PROMPT_CHANGE))
            keyboard.add(B("🚧 Изменить имя", callback_data=CBT_NAME_CHANGE))
            keyboard.add(B("🚧 Изменить Groq Api", callback_data=CBT_API_CHANGE))

            # Helper function to create icon buttons
            def create_icon_button(label, setting_key, switch_key):
                icon = CHECK_MARK if SETTINGS[setting_key] else CROSS_MARK
                return [
                    B(label, callback_data=f"{CBT_SWITCH}:{switch_key}"),
                    B(icon, callback_data=f"{CBT_SWITCH}:{switch_key}_icon")
                ]

            # Настройка отправки ответа
            keyboard.row(*create_icon_button("Включен:", 'send_response', 'send_response'))

            # Настройка дескриптора черного списка
            keyboard.row(*create_icon_button("Отвечать ЧСникам:", 'black_list_handle', 'black_list_handle'))

            # Уведомить о настройке telegram
            keyboard.row(*create_icon_button("Уведомления:", 'notify_telegram', 'notify_telegram'))

            # Кнопка "Проверить обновления"
            keyboard.row(B("🔄 Проверить обновления", callback_data=CHECK_UPDATES))

            # Кнопка "Назад"
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
            github_repo = "alex117815/FPC-seller_gpt"  # repo
            update_message = check_and_update_package(github_repo)

            bot.answer_callback_query(call.id, text=update_message)
        except Exception as e:
            logger.error(e)
            bot.answer_callback_query(call.id, text="Произошла ошибка при выполнении хэндлера Telegram бота.")

    def toggle_send_response(call: telebot.types.CallbackQuery):
        try:
            SETTINGS["notify_chatid"] = call.message.chat.id
            SETTINGS["send_response"] = not SETTINGS.get("send_response", False)
            save_config()
            settings(call)
        except Exception as e:
            logger.error(e)

    def toggle_notify_telegram(call: telebot.types.CallbackQuery):
        try:
            SETTINGS["notify_chatid"] = call.message.chat.id
            SETTINGS["notify_telegram"] = not SETTINGS.get("notify_telegram", False)
            save_config()
            settings(call)
        except Exception as e:
            logger.error(e)

    def toggle_handle_black_listed_users(call: telebot.types.CallbackQuery):
        try:
            SETTINGS["notify_chatid"] = call.message.chat.id
            SETTINGS["black_list_handle"] = not SETTINGS.get("black_list_handle", False)
            save_config()
            settings(call)
        except Exception as e:
            logger.error(e)

    def edit(call: telebot.types.CallbackQuery):
        result = bot.send_message(call.message.chat.id,
                                f"<b>🌈 Текущее значение:</b> {SETTINGS['prompt']}\n\n"
                                f"🔽 Введите новый промпт 🔽",
                                reply_markup=tg_bot.static_keyboards.CLEAR_STATE_BTN())
        tg.set_state(call.message.chat.id, result.id, call.from_user.id,
                    f"{CBT_PROMPT_EDITED}")
        bot.answer_callback_query(call.id)

    def edited_key(message: telebot.types.Message):
        text = message.text
        key = "prompt"
        try:
            # Предполагая, что message.text является новым промптом
            if not isinstance(text, str) or len(text) == 0:
                raise ValueError("🔴 Недопустимый формат промпта")
            new_prompt_key = text
        except ValueError as e:
            logger.info(e)
            bot.reply_to(message, f"🔴 Неправильный формат. Попробуйте снова.",
                        reply_markup=tg_bot.static_keyboards.CLEAR_STATE_BTN())
            return
        tg.clear_state(message.chat.id, message.from_user.id, True)
        keyboard = K().row(B("◀️ Назад", callback_data=f"{CBT.PLUGIN_SETTINGS}:{UUID}"))
        SETTINGS[key] = new_prompt_key
        save_config()
        bot.reply_to(message, f"✅ Успех: {new_prompt_key}", reply_markup=keyboard)

    def edit_username(call: telebot.types.CallbackQuery):
        result = bot.send_message(call.message.chat.id,
                                f"<b>🌈 Текущее значение:</b> {SETTINGS['username']}\n\n"
                                f"🔽 Введите свой ник 🔽",
                                reply_markup=tg_bot.static_keyboards.CLEAR_STATE_BTN())
        tg.set_state(call.message.chat.id, result.id, call.from_user.id,
                    f"{CBT_NAME_EDITED}")
        bot.answer_callback_query(call.id)

    def edited_username(message: telebot.types.Message):
        text = message.text
        key = "username"
        try:
            # Предполагая, что message.text является новым промптом
            if not isinstance(text, str) or len(text) == 0:
                raise ValueError("🔴 Недопустимый формат промпта")
            new_prompt_key = text
        except ValueError as e:
            logger.info(e)
            bot.reply_to(message, f"🔴 Неправильный формат. Попробуйте снова.",
                        reply_markup=tg_bot.static_keyboards.CLEAR_STATE_BTN())
            return
        tg.clear_state(message.chat.id, message.from_user.id, True)
        keyboard = K().row(B("◀️ Назад", callback_data=f"{CBT.PLUGIN_SETTINGS}:{UUID}"))
        SETTINGS[key] = new_prompt_key
        save_config()
        bot.reply_to(message, f"✅ Успех: {new_prompt_key}", reply_markup=keyboard)

    def edit_api(call: telebot.types.CallbackQuery):
        result = bot.send_message(call.message.chat.id,
                                f"<b>🌈 Текущее значение:</b> {SETTINGS['groqapi']}\n\n"
                                f"Api брать с сайта: https://groq.com/"
                                f"🔽 Введите новый api 🔽",
                                
                                reply_markup=tg_bot.static_keyboards.CLEAR_STATE_BTN())
        tg.set_state(call.message.chat.id, result.id, call.from_user.id,
                    f"{CBT_API_EDITED}")
        bot.answer_callback_query(call.id)

    def edited_api(message: telebot.types.Message):
        text = message.text
        key = "groqapi"
        try:
            # Предполагая, что message.text является новым промптом
            if not isinstance(text, str) or len(text) == 0:
                raise ValueError("🔴 Недопустимый формат groqapi")
            new_prompt_key = text
        except ValueError as e:
            logger.info(e)
            bot.reply_to(message, f"🔴 Неправильный формат. Попробуйте снова.",
                        reply_markup=tg_bot.static_keyboards.CLEAR_STATE_BTN())
            return
        tg.clear_state(message.chat.id, message.from_user.id, True)
        keyboard = K().row(B("◀️ Назад", callback_data=f"{CBT.PLUGIN_SETTINGS}:{UUID}"))
        SETTINGS[key] = new_prompt_key
        save_config()
        bot.reply_to(message, f"✅ Успех: {new_prompt_key}", reply_markup=keyboard)

    #Менять промпт
    tg.cbq_handler(edit, lambda c: CBT_PROMPT_CHANGE in c.data)
    tg.msg_handler(edited_key, func=lambda m: tg.check_state(m.chat.id, m.from_user.id, f"{CBT_PROMPT_EDITED}"))
    #Менять ник
    tg.cbq_handler(edit_username, lambda c: CBT_NAME_CHANGE in c.data)
    tg.msg_handler(edited_username, func=lambda m: tg.check_state(m.chat.id, m.from_user.id, f"{CBT_NAME_EDITED}"))
    #Groq api
    tg.cbq_handler(edit_api, lambda c: CBT_API_CHANGE in c.data)
    tg.msg_handler(edited_api, func=lambda m: tg.check_state(m.chat.id, m.from_user.id, f"{CBT_API_EDITED}"))
    #Переключатели
    tg.cbq_handler(toggle_send_response, lambda c: f"{CBT_SWITCH}:send_response" in c.data)
    tg.cbq_handler(toggle_handle_black_listed_users, lambda c: f"{CBT_SWITCH}:black_list_handle" in c.data)
    tg.cbq_handler(toggle_notify_telegram, lambda c: f"{CBT_SWITCH}:notify_telegram" in c.data)
    #Сеттингс
    tg.cbq_handler(switch, lambda c: CBT_SWITCH in c.data)
    tg.cbq_handler(settings, lambda c: f"{CBT.PLUGIN_SETTINGS}:{UUID}" in c.data)
    #Updates
    tg.cbq_handler(handle_update, lambda c: CHECK_UPDATES in c.data)

#Бинды
BIND_TO_NEW_MESSAGE = [bind_to_new_message]
BIND_TO_DELETE = None
BIND_TO_PRE_INIT = [init]
