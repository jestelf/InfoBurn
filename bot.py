# bot.py
import telebot
import config
from handlers.command_handlers import register_command_handlers
from handlers.callback_handlers import register_callback_handlers
from handlers.message_handlers import register_message_handlers
import time
import requests
import logging
from utils.data_manager import load_data, save_data

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,  # Уровень логирования
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),  # Запись логов в файл
        logging.StreamHandler()          # Вывод логов в консоль
    ]
)

logger = logging.getLogger(__name__)

def start_bot():
    bot = telebot.TeleBot(config.BOT_TOKEN)

    # Регистрация обработчиков
    register_command_handlers(bot)
    register_callback_handlers(bot)
    register_message_handlers(bot)

    # Проверка доступа к чату для хранения данных
    try:
        chat = bot.get_chat(config.DATA_CHAT_ID)
        logger.info(f"Доступ к чату для хранения данных подтвержден: {chat.title}")
    except Exception as e:
        logger.error(f"Не удалось получить доступ к чату для хранения данных: {e}")
        return

    # Инициализация данных
    try:
        data = load_data()
        save_data(data)  # Обновляем файл данных
        logger.info("Данные инициализированы.")
    except Exception as e:
        logger.error(f"Ошибка при инициализации данных: {e}")

    # Запуск бота с обработкой возможных исключений
    while True:
        try:
            logger.info("Бот запущен и ожидает обновлений...")
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except requests.exceptions.ReadTimeout:
            logger.warning("Превышено время ожидания. Перезапуск...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Произошла ошибка: {e}")
            time.sleep(5)

if __name__ == "__main__":
    start_bot()
