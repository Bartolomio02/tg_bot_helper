import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import os

from .handlers import router
from .middleware import RateLimitMiddleware, get_operator_ids

# Налаштування логування
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Завантаження змінних середовища
load_dotenv()

# Токен бота зі змінної середовища
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    raise ValueError("Токен не надано. Встановіть змінну середовища TELEGRAM_BOT_TOKEN.")

# Перевірка наявності операторів
operator_ids = get_operator_ids()
if not operator_ids:
    raise ValueError("Не знайдено жодного оператора. Встановіть змінну середовища OPERATOR_IDS у форматі: id1,id2,id3")

# Ініціалізація бота та диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Конфігурація для middleware та handlers
config = {
    "OPERATOR_IDS": operator_ids
}

# Реєстрація middleware
dp.message.middleware(RateLimitMiddleware())

# Реєстрація обробників
dp.include_router(router)

async def main():
    logging.info("Запуск бота...")
    try:
        # Видалення вебхука перед початком опитування
        await bot.delete_webhook(drop_pending_updates=True)
        # Початок опитування з передачою конфігурації
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types(), config=config)
    except Exception as e:
        logging.error(f"Критична помилка: {e}")
        raise
    finally:
        logging.info("Бот зупинений")
        await bot.session.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот зупинений користувачем/системою")
    except Exception as e:
        logging.error(f"Фатальна помилка: {e}")
