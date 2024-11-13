from datetime import datetime
import os
import logging
import asyncio
from aiogram import F, Router
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from static import messages
from .keyboard import get_main_keyboard, get_yes_no_keyboard, get_continue_keyboard
from .fsm import UserForm, ChatMode, MediaForm, OtherPeopleHelpForm
from .middleware import get_operator_ids
from .user_access import user_access

router = Router()

# Словник для зберігання таймерів користувачів
user_timers = {}


async def check_timeout(user_id: int, state: FSMContext, message: Message):
    """Перевірка тайм-ауту користувача"""
    await asyncio.sleep(180)  # 3 минуты
    current_state = await state.get_state()

    # Перевіряємо, чи користувач все ще в процесі заповнення форми
    if current_state in [
        UserForm.waiting_for_name,
        UserForm.waiting_for_age,
        UserForm.waiting_for_location,
        UserForm.waiting_for_event_details,
        UserForm.waiting_for_help_type,
        UserForm.waiting_for_description
    ]:
        await message.answer(
            "❓ <b>Продовжимо?</b>",
            reply_markup=get_yes_no_keyboard(),
            parse_mode="HTML"
        )
        # Встановлюємо стан очікування відповіді про продовження
        await state.set_state("waiting_continue")


def extract_user_id(message: Message) -> int:
    """Отримати ID користувача з повідомлення або пересланого повідомлення"""
    try:
        if message.forward_from:
            return message.forward_from.id
        if message.text and "ID: " in message.text:
            id_part = message.text.split("ID: ")[1].split("\n")[0]
            return int(id_part)
    except (IndexError, ValueError, AttributeError):
        print(f"Помилка при отриманні ID користувача з повідомлення: {message}")
        return None
    return None


async def forward_to_operators(message: Message, user_context: str = None):
    """Переслати повідомлення всім операторам з контекстом користувача"""
    operator_ids = get_operator_ids()

    for operator_id in operator_ids:
        try:
            forwarded = await message.forward(operator_id)
            notification = (
                f"<b>Повідомлення від користувача:</b>\n"
                f"📋 <b>ID:</b> <code>{message.from_user.id}</code>\n"
                f"👤 <b>Ім'я:</b> {message.from_user.full_name}\n"
                f"📱 <b>Username:</b> @{message.from_user.username}"
            )
            if user_context:
                notification += f"\n📝 <b>Контекст:</b> <i>{user_context}</i>"
            await message.bot.send_message(operator_id, notification, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Помилка при пересиланні повідомлення оператору {operator_id}: {e}")


async def forward_to_user(message: Message, user_id: int):
    """Переслати повідомлення оператора користувачу"""
    if user_access.is_blocked(user_id):
        await message.answer(
            f"❌ <b>Неможливо надіслати повідомлення. Користувач</b> <code>{user_id}</code> <b>заблокований.</b>",
            parse_mode="HTML"
        )
        return
    await message.copy_to(user_id)


@router.message(Command("block"))
async def block_user_handler(message: Message):
    """Обробка команди блокування користувача"""
    if message.from_user.id not in get_operator_ids():
        return

    try:
        args = message.text.split()
        if len(args) != 2:
            await message.answer(
                "❌ <b>Використання:</b> /block ID_користувача\n"
                "Наприклад: /block 123456789",
                parse_mode="HTML"
            )
            return

        user_id = int(args[1])
        if user_access.block_user(user_id):
            await message.answer(
                f"✅ <b>Користувача з ID</b> <code>{user_id}</code> <b>заблоковано</b>",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"ℹ️ <b>Користувач з ID</b> <code>{user_id}</code> <b>вже заблокований</b>",
                parse_mode="HTML"
            )
    except ValueError:
        await message.answer(
            "❌ <b>Помилка: Некоректний ID користувача</b>",
            parse_mode="HTML"
        )


@router.message(Command("unblock"))
async def unblock_user_handler(message: Message):
    """Обробка команди розблокування користувача"""
    if message.from_user.id not in get_operator_ids():
        return

    try:
        args = message.text.split()
        if len(args) != 2:
            await message.answer(
                "❌ <b>Використання:</b> /unblock ID_користувача\n"
                "Наприклад: /unblock 123456789",
                parse_mode="HTML"
            )
            return

        user_id = int(args[1])
        if user_access.unblock_user(user_id):
            await message.answer(
                f"✅ <b>Користувача з ID</b> <code>{user_id}</code> <b>розблоковано</b>",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"ℹ️ <b>Користувач з ID</b> <code>{user_id}</code> <b>не був заблокований</b>",
                parse_mode="HTML"
            )
    except ValueError:
        await message.answer(
            "❌ <b>Помилка: Некоректний ID користувача</b>",
            parse_mode="HTML"
        )


@router.message(Command("blocked_list"))
async def blocked_list_handler(message: Message):
    """Обробка команди перегляду списку заблокованих користувачів"""
    if message.from_user.id not in get_operator_ids():
        return

    blocked_users = user_access.get_blocked_users()
    if not blocked_users:
        await message.answer(
            "ℹ️ <b>Список заблокованих користувачів порожній</b>",
            parse_mode="HTML"
        )
        return

    blocked_list = "\n".join([f"• <code>{user_id}</code>" for user_id in blocked_users])
    await message.answer(
        f"📋 <b>Список заблокованих користувачів:</b>\n\n{blocked_list}",
        parse_mode="HTML"
    )


@router.message(Command("help"))
async def help_handler(message: Message):
    """Обробка команди /help"""
    help_text = (
        "🤖 <b>Допомога з використання бота:</b>\n\n"
        "📝 <b>Основні команди:</b>\n"
        "/start - Почати спілкування\n"
        "/help - Показати цю довідку\n"
        "/cancel - Скасувати поточну дію\n"
    )

    # Додаткові команди для операторів
    if message.from_user.id in get_operator_ids():
        help_text += (
            "\n📋 <b>Команди для операторів:</b>\n"
            "/block ID - Заблокувати користувача\n"
            "/unblock ID - Розблокувати користувача\n"
            "/blocked_list - Показати список заблокованих користувачів\n"
        )

    help_text += (
        "\nℹ️ <b>Додаткова інформація:</b>\n"
        "- Для отримання допомоги виберіть відповідний пункт меню\n"
        "- Всі ваші дані обробляються конфіденційно\n"
        "- Координатори доступні з 9:00 до 20:00\n"
        "- В неробочий час ви можете залишити своє звернення"
    )

    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext):
    """Обробка команди /cancel"""
    if user_access.is_blocked(message.from_user.id):
        await message.answer(
            "❌ <b>На жаль, ваш доступ до бота обмежено.</b>",
            parse_mode="HTML"
        )
        return

    current_state = await state.get_state()
    if current_state is None:
        return

    # Скасуємо таймер, якщо він існує
    if message.from_user.id in user_timers:
        user_timers[message.from_user.id].cancel()
        del user_timers[message.from_user.id]

    await state.clear()
    await message.answer(
        "❌ <b>Поточну дію скасовано.</b>\n"
        "Щоб почати спочатку, використайте команду /start",
        parse_mode="HTML"
    )


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    """Обробка команди /start"""
    if user_access.is_blocked(message.from_user.id):
        await message.answer(
            "❌ <b>На жаль, ваш доступ до бота обмежено.</b>",
            parse_mode="HTML"
        )
        return

    # Перевірка чи це оператор
    if message.from_user.id in get_operator_ids():
        await message.answer(
            "👋 <b>Вітаємо!</b>\n\n"
            "Для перегляду доступних команд використовуйте /help\n"
            "Ви можете відповідати на повідомлення користувачів та керувати їх доступом.",
            parse_mode="HTML"
        )
        return

    current_hour = datetime.now().hour

    # Сповіщення операторів про новий чат
    notification = (
        f"🆕 <b>Новий чат створено:</b>\n"
        f"📋 <b>ID:</b> <code>{message.from_user.id}</code>\n"
        f"👤 <b>Ім'я:</b> {message.from_user.full_name}\n"
        f"📱 <b>Username:</b> @{message.from_user.username}"
    )
    for operator_id in get_operator_ids():
        try:
            await message.bot.send_message(operator_id, notification, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Помилка при надсиланні сповіщення оператору {operator_id}: {e}")

    if 9 <= current_hour <= 20:
        # Робочі години
        await state.set_state(ChatMode.automated)
        await message.answer(messages.main_message_online, reply_markup=get_main_keyboard(), parse_mode="HTML")
    else:
        # Неробочі години
        await state.set_state(ChatMode.waiting_urgent)
        await message.answer(messages.main_message_offline, reply_markup=get_yes_no_keyboard(), parse_mode="HTML")


@router.message(ChatMode.waiting_urgent, F.text.casefold() == "так")
async def handle_urgent_yes(message: Message, state: FSMContext):
    """Обробка термінової допомоги"""
    if user_access.is_blocked(message.from_user.id):
        await message.answer(
            "❌ <b>На жаль, ваш доступ до бота обмежено.</b>",
            parse_mode="HTML"
        )
        return

    await message.answer(messages.help_message_offline_one, parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
    # Очікуємо 15 секунд
    await asyncio.sleep(15)
    await message.answer(messages.help_message_offline_two, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    await asyncio.sleep(7)
    await message.answer(messages.main_message_online, parse_mode="HTML")
    await asyncio.sleep(15)
    await message.answer(messages.start_form_message, parse_mode="HTML")
    await asyncio.sleep(3)
    await message.answer(messages.ask_name_form_message, parse_mode="HTML")

    await state.set_state(UserForm.waiting_for_name)

    # Запускаем таймер для проверки тайм-аута
    user_timers[message.from_user.id] = asyncio.create_task(
        check_timeout(message.from_user.id, state, message)
    )


@router.message(ChatMode.waiting_urgent, F.text.casefold() == "ні")
async def handle_urgent_no(message: Message, state: FSMContext):
    """Обробка нетермінової допомоги"""
    if user_access.is_blocked(message.from_user.id):
        await message.answer(
            "❌ <b>На жаль, ваш доступ до бота обмежено.</b>",
            parse_mode="HTML"
        )
        return

    await state.set_state(UserForm.waiting_for_name)
    await message.answer(messages.main_message_online, parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(3)
    await message.answer(messages.start_form_message, parse_mode="HTML")
    await message.answer(messages.ask_name_form_message, parse_mode="HTML")

    # Запускаем таймер для проверки тайм-аута
    user_timers[message.from_user.id] = asyncio.create_task(
        check_timeout(message.from_user.id, state, message)
    )


@router.message(ChatMode.automated)
async def handle_menu_choice(message: Message, state: FSMContext):
    """Обробка вибору меню та початок форми"""
    if user_access.is_blocked(message.from_user.id):
        await message.answer(
            "❌ <b>На жаль, ваш доступ до бота обмежено.</b>",
            parse_mode="HTML"
        )
        return

    if not message.text:
        await message.answer("❌ <b>Будь ласка, використовуйте текстові повідомлення</b>", parse_mode="HTML")
        return

    # Спочатку обробляємо спеціальні опції меню
    if "5️⃣" in message.text:
        await state.set_state(MediaForm.waiting_for_media)
        await message.answer(messages.media_message, parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
        return
    elif "6️⃣" in message.text:
        await state.set_state(OtherPeopleHelpForm.waiting_for_other_people_help_message)
        await message.answer(messages.other_people_help_message, parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
        return

    # Починаємо форму тільки для опцій меню 1-4
    if any(num in message.text for num in ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]):
        await state.set_state(UserForm.waiting_for_name)
        await message.answer(messages.start_form_message, parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
        # Очікуємо 10 секунд
        await asyncio.sleep(10)
        await message.answer(messages.ask_name_form_message, parse_mode="HTML", reply_markup=ReplyKeyboardRemove())

        # Запускаємо таймер для перевірки тайм-ауту
        user_timers[message.from_user.id] = asyncio.create_task(
            check_timeout(message.from_user.id, state, message)
        )


@router.message(UserForm.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """Обробка імені користувача"""
    if user_access.is_blocked(message.from_user.id):
        await message.answer(
            "❌ <b>На жаль, ваш доступ до бота обмежено.</b>",
            parse_mode="HTML"
        )
        return

    if not message.text:
        await message.answer("❌ <b>Будь ласка, введіть ваше ім'я текстом</b>", parse_mode="HTML")
        return
    # Скасуємо попередній таймер
    if message.from_user.id in user_timers:
        user_timers[message.from_user.id].cancel()

    await state.update_data(name=message.text)
    await state.set_state(UserForm.waiting_for_age)
    # очікуємо 3 секунд
    await asyncio.sleep(3)
    await message.answer(messages.ask_age_form_message, parse_mode="HTML")

    # Запускаємо новий таймер
    user_timers[message.from_user.id] = asyncio.create_task(
        check_timeout(message.from_user.id, state, message)
    )


@router.message(UserForm.waiting_for_age)
async def process_age(message: Message, state: FSMContext):
    """Обробка віку користувача"""
    if user_access.is_blocked(message.from_user.id):
        await message.answer(
            "❌ <b>На жаль, ваш доступ до бота обмежено.</b>",
            parse_mode="HTML"
        )
        return

    if not message.text:
        await message.answer("❌ <b>Будь ласка, введіть ваш вік числом</b>", parse_mode="HTML")
        return

    try:
        age = int(message.text)
        if age < 1 or age > 120:
            raise ValueError("Invalid age range")

        # Скасуємо попередній таймер
        if message.from_user.id in user_timers:
            user_timers[message.from_user.id].cancel()

        await state.update_data(age=age)
        # очікуємо 3 секунд
        await asyncio.sleep(3)
        await state.set_state(UserForm.waiting_for_location)
        await message.answer(messages.ask_geo_form_message, parse_mode="HTML")

        # Запускаємо новий таймер
        user_timers[message.from_user.id] = asyncio.create_task(
            check_timeout(message.from_user.id, state, message)
        )
    except ValueError:
        await message.answer("❌ <b>Будь ласка, введіть коректний вік числом</b>", parse_mode="HTML")


@router.message(UserForm.waiting_for_location)
async def process_location(message: Message, state: FSMContext):
    """Обробка місцезнаходження користувача"""
    if user_access.is_blocked(message.from_user.id):
        await message.answer(
            "❌ <b>На жаль, ваш доступ до бота обмежено.</b>",
            parse_mode="HTML"
        )
        return

    if not message.text:
        await message.answer("❌ <b>Будь ласка, введіть ваше місцезнаходження текстом</b>", parse_mode="HTML")
        return

    # Скасуємо попередній таймер
    if message.from_user.id in user_timers:
        user_timers[message.from_user.id].cancel()

    await state.update_data(location=message.text)
    await state.set_state(UserForm.waiting_for_event_details)
    # очікуємо 3 секунд
    await asyncio.sleep(3)
    await message.answer(messages.ask_where_form_message, parse_mode="HTML")

    # Запускаємо новий таймер
    user_timers[message.from_user.id] = asyncio.create_task(
        check_timeout(message.from_user.id, state, message)
    )


@router.message(UserForm.waiting_for_event_details)
async def process_event_details(message: Message, state: FSMContext):
    """Обробка деталей події"""
    if user_access.is_blocked(message.from_user.id):
        await message.answer(
            "❌ <b>На жаль, ваш доступ до бота обмежено.</b>",
            parse_mode="HTML"
        )
        return

    if not message.text:
        await message.answer("❌ <b>Будь ласка, опишіть деталі події текстом</b>", parse_mode="HTML")
        return

    # Скасуємо попередній таймер
    if message.from_user.id in user_timers:
        user_timers[message.from_user.id].cancel()

    await state.update_data(event_details=message.text)
    await state.set_state(UserForm.waiting_for_help_type)
    # очікуємо 3 секунд
    await asyncio.sleep(3)
    await message.answer(messages.ask_what_form_message, parse_mode="HTML")

    # Запускаємо новий таймер
    user_timers[message.from_user.id] = asyncio.create_task(
        check_timeout(message.from_user.id, state, message)
    )


@router.message(UserForm.waiting_for_help_type)
async def process_help_type(message: Message, state: FSMContext):
    """Обробка типу допомоги"""
    if user_access.is_blocked(message.from_user.id):
        await message.answer(
            "❌ <b>На жаль, ваш доступ до бота обмежено.</b>",
            parse_mode="HTML"
        )
        return

    if not message.text:
        await message.answer("❌ <b>Будь ласка, опишіть потрібну допомогу текстом</b>", parse_mode="HTML")
        return

    # Скасуємо попередній таймер
    if message.from_user.id in user_timers:
        user_timers[message.from_user.id].cancel()

    await state.update_data(help_type=message.text)
    await state.set_state(UserForm.waiting_for_description)
    # очікуємо 3 секунд
    await asyncio.sleep(3)
    await message.answer(messages.ask_description_form_message, parse_mode="HTML")

    # Запускаємо новий таймер
    user_timers[message.from_user.id] = asyncio.create_task(
        check_timeout(message.from_user.id, state, message)
    )


@router.message(UserForm.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    """Обробка опису та завершення форми"""
    if user_access.is_blocked(message.from_user.id):
        await message.answer(
            "❌ <b>На жаль, ваш доступ до бота обмежено.</b>",
            parse_mode="HTML"
        )
        return

    if not message.text:
        await message.answer("❌ <b>Будь ласка, надайте опис текстом</b>", parse_mode="HTML")
        return

    # Скасуємо таймер при завершенні форми
    if message.from_user.id in user_timers:
        user_timers[message.from_user.id].cancel()
        del user_timers[message.from_user.id]

    user_data = await state.get_data()
    await state.update_data(description=message.text)

    # Надсилаємо сповіщення про завершення форми операторам
    notification = (
        f"📋 <b>Форма заповнена:</b>\n\n"
        f"📌 <b>ID:</b> <code>{message.from_user.id}</code>\n"
        f"👤 <b>Ім'я:</b> {user_data['name']}\n"
        f"📅 <b>Вік:</b> {user_data['age']}\n"
        f"📍 <b>Місцезнаходження:</b> {user_data['location']}\n"
        f"🔍 <b>Деталі події:</b> {user_data['event_details']}\n"
        f"🆘 <b>Тип допомоги:</b> {user_data['help_type']}\n"
        f"📝 <b>Опис:</b> <i>{message.text}</i>"
    )

    for operator_id in get_operator_ids():
        try:
            await message.bot.send_message(operator_id, notification, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Помилка при надсиланні сповіщення оператору {operator_id}: {e}")

    # Встановлюємо ручний режим чату та надсилаємо фінальне повідомлення
    await state.set_state(ChatMode.manual)
    await message.answer(messages.final_form_message, parse_mode="HTML")


@router.message(MediaForm.waiting_for_media)
async def process_media(message: Message, state: FSMContext):
    """Обробка повідомленнь від представників організацій та медіа"""
    if user_access.is_blocked(message.from_user.id):
        await message.answer(
            "❌ <b>На жаль, ваш доступ до бота обмежено.</b>",
            parse_mode="HTML"
        )
        return

    # Пересилаємо заяву операторам
    await forward_to_operators(message, "Представкник організації/медіа")

    # Встановлюємо ручний режим для подальшого спілкування
    await state.set_state(ChatMode.manual)
    await message.answer(
        "✅ <b>Ваше повідомлення успішно передано координатору.</b>\n"
        "Очікуйте на відповідь.",
        parse_mode="HTML"
    )


@router.message(OtherPeopleHelpForm.waiting_for_other_people_help_message)
async def process_other_people_help(message: Message, state: FSMContext):
    """Обробка повідомлення про допомогу іншим"""
    if user_access.is_blocked(message.from_user.id):
        await message.answer(
            "❌ <b>На жаль, ваш доступ до бота обмежено.</b>",
            parse_mode="HTML"
        )
        return

    if not message.text:
        await message.answer(
            "❌ <b>Будь ласка, опишіть ситуацію текстовим повідомленням</b>",
            parse_mode="HTML"
        )
        return

    # Встановлюємо ручний режим для подальшого спілкування
    await state.set_state(ChatMode.manual)


    # Пересилаємо повідомлення операторам
    if message.from_user.id not in get_operator_ids():
        await forward_to_operators(message, "Допомога іншим")
        await message.answer(
            "✅ <b>Ваше повідомлення передано координатору.</b>\nОчікуйте на відповідь.",
            parse_mode="HTML"
        )


@router.message(lambda message: message.text and message.from_user.id in user_timers)
async def handle_continue_response(message: Message, state: FSMContext):
    """Обробка відповіді на запитання щодо продовження заповнення форми"""
    current_state = await state.get_state()

    if current_state == "waiting_continue":
        if message.text.lower() == "ні":
            # Якщо відповідь "Ні", скасовуємо форму
            if message.from_user.id in user_timers:
                user_timers[message.from_user.id].cancel()
                del user_timers[message.from_user.id]
            await state.clear()
            await message.answer(
                "❌ <b>Заповнення форми скасовано.</b>\n"
                "Щоб почати спочатку, використайте команду /start",
                parse_mode="HTML"
            )
        else:

            # Відновлюємо попередній стан та продовжуємо опитування
            user_data = await state.get_data()
            if 'name' not in user_data:
                await state.set_state(UserForm.waiting_for_name)
                await message.answer(messages.ask_name_form_message, parse_mode="HTML",
                                     reply_markup=ReplyKeyboardRemove())
            elif 'age' not in user_data:
                await state.set_state(UserForm.waiting_for_age)
                await message.answer(messages.ask_age_form_message, parse_mode="HTML",
                                     reply_markup=ReplyKeyboardRemove())
            elif 'location' not in user_data:
                await state.set_state(UserForm.waiting_for_location)
                await message.answer(messages.ask_geo_form_message, parse_mode="HTML",
                                     reply_markup=ReplyKeyboardRemove())
            elif 'event_details' not in user_data:
                await state.set_state(UserForm.waiting_for_event_details)
                await message.answer(messages.ask_where_form_message, parse_mode="HTML",
                                     reply_markup=ReplyKeyboardRemove())
            elif 'help_type' not in user_data:
                await state.set_state(UserForm.waiting_for_help_type)
                await message.answer(messages.ask_what_form_message, parse_mode="HTML",
                                     reply_markup=ReplyKeyboardRemove())
            elif 'description' not in user_data:
                await state.set_state(UserForm.waiting_for_description)
                await message.answer(messages.ask_description_form_message, parse_mode="HTML",
                                     reply_markup=ReplyKeyboardRemove())

            # Запускаємо новий таймер
            user_timers[message.from_user.id] = asyncio.create_task(
                check_timeout(message.from_user.id, state, message)
            )


@router.message(ChatMode.manual)
async def handle_manual_mode(message: Message):
    """Обробка повідомлень в ручному режимі"""
    if user_access.is_blocked(message.from_user.id):
        await message.answer(
            "❌ <b>На жаль, ваш доступ до бота обмежено.</b>",
            parse_mode="HTML"
        )
        return

    if message.from_user.id not in get_operator_ids():
        # Якщо повідомлення від користувача, пересилаємо його операторам
        await forward_to_operators(message, "Повідомлення з ручного режиму")


# Обробник для відповідей операторів
@router.message(lambda message: message.from_user.id in get_operator_ids() and message.reply_to_message is not None)
async def handle_operator_reply(message: Message):
    """Обробка відповідей операторів на повідомлення"""
    # Отримуємо ID користувача з оригінального повідомлення
    user_id = extract_user_id(message.reply_to_message)

    if user_id:
        # Пересилаємо відповідь користувачу
        await forward_to_user(message, user_id)
        await message.answer(
            f"✅ <b>Повідомлення надіслано користувачу</b> <code>{user_id}</code>",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ <b>Не вдалося визначити ID користувача для відповіді</b>",
            parse_mode="HTML"
        )


# Обробник для нетекстових повідомлень
@router.message(lambda message: not message.text)
async def handle_non_text(message: Message):
    """Обробка нетекстових повідомлень"""
    if user_access.is_blocked(message.from_user.id):
        await message.answer(
            "❌ <b>На жаль, ваш доступ до бота обмежено.</b>",
            parse_mode="HTML"
        )
        return

    # Якщо повідомлення від оператора і це відповідь
    if message.from_user.id in get_operator_ids() and message.reply_to_message:
        user_id = extract_user_id(message.reply_to_message)
        if user_id:
            await forward_to_user(message, user_id)
            await message.answer(
                f"✅ <b>Медіа надіслано користувачу</b> <code>{user_id}</code>",
                parse_mode="HTML"
            )
            return

    # Для звичайних користувачів
    if message.from_user.id not in get_operator_ids():
        await forward_to_operators(message, "Медіа повідомлення")
        await message.answer(
            "✅ <b>Ваше медіа повідомлення передано координатору</b>",
            parse_mode="HTML"
        )
