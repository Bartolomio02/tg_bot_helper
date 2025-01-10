from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Головна клавіатура меню з 6 опціями"""
    keyboard = [
        [KeyboardButton(text="1️⃣ Консультація щодо допомоги"), KeyboardButton(text="2️⃣ Психологічна допомога")],
        [KeyboardButton(text="3️⃣ Медична допомога"), KeyboardButton(text="4️⃣ Консультація юриста")],
        [KeyboardButton(text="5️⃣ Представник організації/медіа"), KeyboardButton(text="6️⃣ Допомога для близької людини")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_yes_no_keyboard() -> ReplyKeyboardMarkup:
    """Клавіатура Так/Ні для рішення про термінову допомогу"""
    keyboard = [
        [KeyboardButton(text="Так"), KeyboardButton(text="Ні")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_continue_keyboard() -> ReplyKeyboardMarkup:
    """Клавіатура для продовження"""
    keyboard = [
        [KeyboardButton(text="Продовжити")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
