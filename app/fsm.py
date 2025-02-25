from aiogram.fsm.state import State, StatesGroup

class UserForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_age = State()
    waiting_for_location = State()
    waiting_for_event_details = State()
    waiting_for_help_type = State()

class ChatMode(StatesGroup):
    automated = State()
    manual = State()
    waiting_urgent_help = State()  # Для прийняття рішення про термінову допомогу в неробочий час
    waiting_continue_help = State()  # Для продовження допомоги в неробочий час

class MediaForm(StatesGroup):
    waiting_for_media = State()

class OtherPeopleHelpForm(StatesGroup):
    waiting_for_other_people_help_message = State()

