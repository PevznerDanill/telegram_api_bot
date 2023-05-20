import telebot
from telebot import types
from telegram_hotels_bot.user import user

"""
Файл с функциями, создающими клавиатуры для класса Bot в файле my_bot.py.
"""


def initial_keyboard() -> telebot.types.InlineKeyboardMarkup:
    """
    Создает Inline клавиатуру для начала работы с ботом.
    """
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    find_hotel_btn = types.InlineKeyboardButton('Найти отели', callback_data='get_city')
    history_btn = types.InlineKeyboardButton('Показать историю поиска', callback_data='/history')
    keyboard.add(find_hotel_btn, history_btn)
    return keyboard


def rooms_kb() -> telebot.types.InlineKeyboardMarkup:
    """
    Создает Inline клавиатуру для выбора количества бронируемых номеров.
    """
    keyboard = types.InlineKeyboardMarkup(row_width=4)
    buttons = (types.InlineKeyboardButton(text=str(room),
                                          callback_data=f'#rooms{room}') for room in range(1, 9))
    keyboard.add(*buttons)
    return keyboard


def hotels_kb() -> telebot.types.InlineKeyboardMarkup:
    """
    Создает Inline клавиатуру для выбора количества загружаемых отелей.
    """
    keyboard = types.InlineKeyboardMarkup(row_width=4)
    buttons = (types.InlineKeyboardButton(text=str(i_index), callback_data=f'#hotels_amnt#{i_index}')
                   for i_index in range(1, 6))
    keyboard.add(*buttons)
    return keyboard


def photos_kb() -> telebot.types.InlineKeyboardMarkup:
    """
    Создает Inline клавиатуру для выбора количества загружаемых фото отелей.
    """
    keyboard = types.InlineKeyboardMarkup(row_width=4)
    buttons = (types.InlineKeyboardButton(text=str(i_index), callback_data=f'#photos_amnt#{i_index}')
               for i_index in range(1, 6))
    no_button = types.InlineKeyboardButton(text='Без фото', callback_data='#photos_amnt#0')
    keyboard.add(no_button, *buttons)
    return keyboard


def option_choice_keyboard() -> telebot.types.InlineKeyboardMarkup:
    """
    Создает Inline клавиатуру для выбора команды бота.
    """
    keyboard = types.InlineKeyboardMarkup(row_width=1)

    low_price_btn = types.InlineKeyboardButton('Найти самые дешевые отели', callback_data='low_price')
    high_price_btn = types.InlineKeyboardButton('Найти самые дорогие отели', callback_data='high_price')
    best_deal_btn = types.InlineKeyboardButton('Настраиваемый поиск', callback_data='best_deal')
    new_data_btn = types.InlineKeyboardButton('Ввести другие данные', callback_data='new_data')
    keyboard.add(low_price_btn, high_price_btn, best_deal_btn, new_data_btn)
    return keyboard


def again_option_choice_keyboard():
    """
    Создает Inline клавиатуру для повторного выбора команды бота.
    """
    keyboard = types.InlineKeyboardMarkup(row_width=1)

    low_price_btn = types.InlineKeyboardButton('Найти самые дешевые отели', callback_data='again_low_price')
    high_price_btn = types.InlineKeyboardButton('Найти самые дорогие отели', callback_data='again_high_price')
    best_deal_btn = types.InlineKeyboardButton('Настраиваемый поиск', callback_data='again_best_deal')
    new_data_btn = types.InlineKeyboardButton('Ввести другие данные', callback_data='new_data')
    history_btn = types.InlineKeyboardButton('Показать историю поиска', callback_data='/history')
    keyboard.add(low_price_btn, high_price_btn, best_deal_btn, new_data_btn, history_btn)
    return keyboard
