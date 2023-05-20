import telebot
from telebot import TeleBot, types
from telegram_hotels_bot.utils import cities_offer
from telegram_hotels_bot.bot import main_keyboard, greetings, location_search, commands
from telegram_hotels_bot.api_requests.api_requests import get_converted_price
from telegram_hotels_bot.user import user
from datetime import datetime, timedelta, date
import time
from babel.dates import format_date
from telegram_bot_calendar import DetailedTelegramCalendar
import re
from typing import List
import os
import pickle
from telegram_hotels_bot import config


TSTEP = {'y': 'год', 'm': 'месяц', 'd': 'день'}


class MyBot:
    """
    Класс MyBot. Описывает поведение телеграмм-бота, функционирующего на базе pyTelegramBotAPI.

    Arguments:
        self.bot (TeleBot): бот TeleBot с токеном.
        self.cache (Optional[Any]): переменная для временного хранения данных перед их
        записью в класс User.
    """

    def __init__(self):

        token = config.TOKEN

        self.bot = TeleBot(f'{token}', parse_mode=None)
        self.cache = None

        @self.bot.message_handler(commands=['help'])
        def give_help(message: telebot.types.Message) -> None:
            """
            Рассказывает о функциях бота
            """
            reply_message = 'Для начала работы с ботом, выберите в боковом меню слева комманду start\n' \
                            'Если вы хотите начать новый поиск, нажмите кнопку Найти отели\n' \
                            'После этого вам будет предложено ввести данные необходимые для начала поиска.' \
                            'Следуйте предложенным командам.\n' \
                            'После вы можете выбрать один из вариантов поиска:\n' \
                            'Найти самые дешевые отели: поиск самых дешевых отелей по заданным параметрам\n' \
                            'Найти самые дорогие отели: поиск самых дешевых отелей по заданным параметрам\n' \
                            'Настраиваемый поиск: поиск на основе дополнительных данных (диапазон цены и ' \
                            'удаленности отеля от центра)\n' \
                            'Если вы хотите посмотреть историю поисков, нажмите кнопку Показать историю поиска\n' \
                            ''
            self.bot.send_message(message.chat.id, reply_message)

        @self.bot.message_handler(func=greetings.greetings)
        @self.bot.message_handler(commands=['start'])
        def say_hello(message: telebot.types.Message) -> None:
            """
            Ловит приветственное сообщение от пользователя, проверяет наличие файла history.pickle
            (если нет, то создает) и запускает метод say_hi.
            """

            history_file = os.path.join('history.pickle')

            if not os.path.isfile(history_file):

                with open(history_file, 'wb') as history:
                    all_users = {}
                    pickle.dump(all_users, history)

            self.say_hi(message)

        @self.bot.callback_query_handler(func=lambda callback: callback.data == 'back' or callback.data == 'new_data')
        def go_back(callback: telebot.types.CallbackQuery) -> None:
            """
            Ловит коллбэки back и new_data. Если коллбэк back, то запускает функцию
            clear_last_search, которая удаляет последний поиск.
            Как в случае back, так и new_data, открывает первое меню.
            """
            if callback.data == 'back':
                self.clear_last_search(callback)
            self.initial_keyboard(callback.message.chat.id)

        @self.bot.callback_query_handler(func=lambda callback: callback.data == '/history')
        def show_history(callback: telebot.types.CallbackQuery) -> None:
            """
            Ловит коллбэк с командой history (Показать историю поиска), запускает функцию give_history
            в файле commands, чтобы сформировать сообщение с историей поиска, и если она не пустая
            отправляет Inline клавиатуру с номерами поисков, предлагая повторить его с другой командой, но
            теми же данными.
            """
            history_message = commands.give_history(callback.message.chat.id)
            self.bot.send_message(callback.message.chat.id, history_message)
            cur_user = user.find_user(callback.message.chat.id)

            if len(cur_user.searches) > 0:
                searches_id = (search.search_id for search in cur_user.searches)
                keyboard = types.InlineKeyboardMarkup(row_width=5)
                id_buttons = (types.InlineKeyboardButton(text=f'{search_id}', callback_data=f'#search{search_id}')
                              for search_id in searches_id)
                keyboard.add(*id_buttons)
                keyboard.add(types.InlineKeyboardButton(text='Начать другой поиск', callback_data='new_data'))
                message_text = 'Выберите номер поиска, чтобы осуществить новый поиск с теми же параметрами, ' \
                               'или начните другой поиск'
                self.bot.send_message(callback.message.chat.id, text=message_text, reply_markup=keyboard)

            else:
                keyboard = types.InlineKeyboardMarkup(row_width=1)
                button = types.InlineKeyboardButton('Найти отели', callback_data='get_city')
                keyboard.add(button)
                self.bot.send_message(callback.message.chat.id,
                                      text='Нажмите на кнопку для продолжения работы', reply_markup=keyboard)

        @self.bot.callback_query_handler(func=lambda callback: callback.data == 'get_city')
        def get_city(callback: telebot.types.CallbackQuery) -> None:
            """
            Ловит коллбэк get_city, заложенный в кнопку 'Найти отели' в начальном меню.
            Запускает функцию ask_city, начиная сбор данных для запросов к Hotels Api.
            """
            self.ask_city(callback.message.chat.id)

        @self.bot.callback_query_handler(func=lambda callback: callback.data.startswith('#city'))
        def confirm_city_and_go_check_in(callback: telebot.types.CallbackQuery) -> None:
            """
            Ловит коллбэк с хештегом #city и номером, соответствующему индексу списка городов и их данных,
            сохраненных в переменной cache. Последний элемент списка - 'Другой город', и если число
            после #city совпадает с индексом последнего элемента, то данные из cache удаляются и снова запускается
            функция ask_city. Иначе данные города передаются для сохранения в функцию save_city и запускается
            функция ask_date, которая начинает запрашивать даты заезда и выезда из отеля.
            """
            result = callback.data[5:]

            if int(result) == len(self.cache[1]) - 1:
                self.ask_city(callback.message.chat.id)

            else:
                self.save_city(callback.data, callback.message.chat.id)
                self.ask_date(callback.message.chat.id, check_in=True)

        @self.bot.callback_query_handler(func=DetailedTelegramCalendar.func(calendar_id=1))
        def save_check_in_and_go_check_out(callback: telebot.types.CallbackQuery) -> None:
            """
            Ловит коллбек календаря DetailedTelegramCalendar с датой заезда в отель, сохраняет
            ее в переменную cache и запускает ask_date,
            чтобы спросить дату окончания пребывания в отеле.
            """
            result, key, step = DetailedTelegramCalendar(min_date=date.today(),
                                                         max_date=date(2023, 12, 31),
                                                         locale='ru', calendar_id=1
                                                         ).process(callback.data)
            if not result and key:
                self.bot.edit_message_text(f"Начало проживания в отеле: выберите {TSTEP[step]}",
                                           callback.message.chat.id,
                                           callback.message.message_id,
                                           reply_markup=key)
            elif result:
                text_date = format_date(result, format='full', locale='ru')
                self.bot.edit_message_text(f"Дата заезда в отель: {text_date}",
                                           callback.message.chat.id,
                                           callback.message.message_id)
                self.cache = [result]
                self.ask_date(callback.message.chat.id, check_out=True)

        @self.bot.callback_query_handler(func=DetailedTelegramCalendar.func(calendar_id=2))
        def save_check_out_and_go_rooms(callback: telebot.types.CallbackQuery) -> None:
            """
            Ловит коллбек календаря DetailedTelegramCalendar с датой последнего дня в отеле, сохраняет
            ее в cache и запускает функцию save_date для сохранения дат в класс Search.
            После запускает функцию ask_rooms.
            """
            result, key, step = DetailedTelegramCalendar(min_date=self.cache[0] + timedelta(days=1),
                                                         max_date=date(2023, 12, 31),
                                                         locale='ru', calendar_id=2
                                                         ).process(callback.data)
            if not result and key:
                self.bot.edit_message_text(f"Окончание проживания в отеле: выберите {TSTEP[step]}",
                                           callback.message.chat.id,
                                           callback.message.message_id,
                                           reply_markup=key)
            elif result:
                text_date = format_date(result, format='full', locale='ru')
                self.bot.edit_message_text(f"Последний день в отеле: {text_date}",
                                           callback.message.chat.id,
                                           callback.message.message_id)
                self.cache.append(result)

                self.save_date(chat_id=callback.message.chat.id)
                self.ask_rooms(callback.message.chat.id)

        @self.bot.callback_query_handler(func=lambda callback: callback.data.startswith('#rooms'))
        def generate_rooms(callback: telebot.types.CallbackQuery) -> None:
            """
            Ловит коллбэк с количеством бронируемых номеров, сохраняет в переменную cache
            список из того же количества словарей и запускает функцию get_people, которая
            спрашивает, сколько людей будет жить в каждом номере.
            """
            rooms_num = int(re.search(r's(\d+)\b', callback.data)[1])
            self.cache = [{} for _ in range(rooms_num)]
            self.get_people(callback)

        @self.bot.callback_query_handler(func=lambda callback: callback.data.startswith('#room='))
        def process_people(callback: telebot.types.CallbackQuery) -> None:
            """
            Ловит коллбэк с количеством проживающих в номере
            и соответствующем тэгом (adults/children).
            """
            people_info = callback.data
            room_number = int(re.search(r'=(\d+)@', people_info)[1])
            tag = re.search(r'@([a-z]+)=', people_info)[1]

            people_amnt = int(re.search(r'=(\d+)#', people_info)[1])

            if tag == 'children':
                if people_amnt > 0:
                    self.get_children(children_amnt=people_amnt, cur_room=room_number,
                                      callback=callback, cur_child=1)
                    return

                self.cache[room_number][tag] = []
            else:
                self.cache[room_number][tag] = people_amnt

            self.get_people(callback)

        @self.bot.callback_query_handler(func=lambda callback: callback.data.startswith('#age'))
        def save_children_age(callback: telebot.types.CallbackQuery) -> None:
            """
            Ловит коллбэк с возрастом ребенка.
            """
            age_cur_child = int(re.search(r'age=(\d+)', callback.data)[1])
            cur_room = int(re.search(r'cur_room=(\d+)', callback.data)[1])
            cur_child = int(re.search(r'cur_child=(\d+)', callback.data)[1])
            total_children = int(re.search(r'total_children=(\d+)', callback.data)[1])

            if self.cache[cur_room].get('children', 0) == 0:
                self.cache[cur_room]['children'] = []
            self.cache[cur_room]['children'].insert(cur_child, {'age': age_cur_child})

            if cur_child == total_children:

                self.get_people(callback)

            else:
                self.get_children(cur_child=cur_child + 1, cur_room=cur_room,
                                  children_amnt=total_children, callback=callback)

        @self.bot.callback_query_handler(func=lambda callback: callback.data.startswith('#hotels_amnt'))
        def save_hotels_amnt(callback: telebot.types.CallbackQuery) -> None:
            """
            Ловит коллбэк с количеством отелей, сохраняет его в класс Search и запускает
            функцию ask_photos.
            """
            hotels_amnt = re.search(r'hotels_amnt#(\d+)', callback.data)[1]
            cur_user = user.find_user(callback.message.chat.id)
            cur_search = cur_user.searches.pop()
            cur_search.max_items = int(hotels_amnt)
            cur_user.searches.append(cur_search)
            user.save_users(cur_user)
            self.ask_photos(callback.message.chat.id)

        @self.bot.callback_query_handler(func=lambda callback: callback.data.startswith('#photos_amnt'))
        def save_photos_amnt_and_ask_commands(callback: telebot.types.CallbackQuery) -> None:
            """
            Ловит количество фотографий, которые будут загружаться в чат, и запускает
            функцию ask_commands.
            """
            photos_amnt = re.search(r'photos_amnt#(\d+)', callback.data)[1]
            cur_user = user.find_user(callback.message.chat.id)
            cur_search = cur_user.searches.pop()
            cur_search.photos_amnt = int(photos_amnt)
            cur_user.searches.append(cur_search)
            user.save_users(cur_user)
            self.ask_commands(callback.message.chat.id)

        @self.bot.callback_query_handler(func=lambda callback: callback.data.endswith('_price'))
        def show_list_price(callback: telebot.types.CallbackQuery) -> None:
            """
            Ловит коллбэк с нажатием кнопок команд 'Найти дешевые отели' (low_price) и
            'Найти самые дорогие отели' (high_price), отправляет сообщение в чат о том,
            что начался поиск, сохраняет в переменную search_results
            результат запроса, сделанного в функции price_list в файле commands.
            После запускает функцию send_price_results.
            """
            self.bot.send_message(callback.message.chat.id, 'Уже ищу! (Поиск может занять до 2 минут, '
                                                            'но я постараюсь быстрее)')
            self.bot.send_message(callback.message.chat.id, '\u23F3')

            cur_user = user.find_user(callback.message.chat.id)
            if callback.data.startswith('again'):
                cur_search = cur_user.searches[-1]
                cur_search = cur_search.update_search()
            else:
                cur_search = cur_user.searches.pop()

            if callback.data.endswith('low_price'):
                cur_search.type_of_search = 'Поиск дешевых отелей'

                updated_search = commands.price_list(cur_search, low_price=True)

            else:
                cur_search.type_of_search = 'Поиск дорогих отелей'
                updated_search = commands.price_list(cur_search, high_price=True)

            if isinstance(updated_search, str):
                message_text = updated_search
                if callback.data.startswith('again'):
                    keyboard = main_keyboard.again_option_choice_keyboard()
                else:
                    keyboard = main_keyboard.option_choice_keyboard()
                self.bot.send_message(callback.message.chat.id, text=message_text, reply_markup=keyboard)
                return

            cur_user.searches.append(updated_search)

            user.save_users(cur_user)

            self.send_price_results(callback.message.chat.id, updated_search.results)

        @self.bot.callback_query_handler(func=lambda callback: callback.data.endswith('best_deal'))
        def start_best_deal(callback: telebot.types.CallbackQuery) -> None:
            """
            Начинает команду bestdeal ("Настраиваемый поиск"). Если пойманный коллбэк начинается с
            again, то создает новый поиск с параметрами предыдущего. После запускает функцию
            ask_price_min.
            """

            cur_user = user.find_user(callback.message.chat.id)
            if callback.data.startswith('again'):
                cur_search = cur_user.searches[-1]
                cur_search = cur_search.update_search()
            else:
                cur_search = cur_user.searches.pop()

            cur_search.type_of_search = 'Настраиваемый поиск'

            cur_user.searches.append(cur_search)
            user.save_users(cur_user)

            self.ask_price_min(callback.message.chat.id)

        @self.bot.callback_query_handler(func=lambda callback: callback.data.startswith('#search'))
        def new_search_old_data(callback: telebot.types.CallbackQuery) -> None:
            """
            Ловит коллбэк с идентификационным номером поиска, создает новый поиск с параметрами
            предыдущего, сохраняет его и спрашивает у пользователя через Inline клавиатуру следующую
            команду
            """
            search_id = re.search(r'ch(\d+)', callback.data)[1]
            cur_user = user.find_user(callback.message.chat.id)
            old_search = [search for search in cur_user.searches if search.search_id == search_id][0]
            new_search = old_search.update_search()
            cur_user.searches.append(new_search)
            keyboard = main_keyboard.option_choice_keyboard()
            message_text = 'Выберите дальнейшее действие'
            self.bot.send_message(callback.message.chat.id, text=message_text, reply_markup=keyboard)

    def start(self) -> None:
        """
        Запускает функцию pooling, обернутую в try-except внутри цикла while, чтобы избежать падения бота.
        """
        while True:
            try:
                self.bot.polling(non_stop=True)
            except Exception as exc:
                print('Some problem occurred')
                print(exc)
                print('restarting the bot in 3 seconds')
                time.sleep(3)

    def say_hi(self, message: telebot.types.Message) -> None:
        """
        Заводит переменную hello, формируемую в функции say_hi_and_remember в файле greetings,
        и отвечает ею на приветствие пользователя. После запускает функцию initial_keyboard.
        """
        hello = greetings.say_hi_and_remember(message)
        self.bot.reply_to(message, hello)
        self.initial_keyboard(message.chat.id)

    def initial_keyboard(self, chat_id: int) -> None:
        """
        Заводит клавиатуру в переменной keyboard, формируемую в функции initial_keyboard в файле
        main_keyboard, и отправляет ее в чат, предлагая пользователю выбрать одну из
        команд для работы.
        :param chat_id: идентификационный номер чата, используемый для отправки сообщения.
        """
        keyboard = main_keyboard.initial_keyboard()
        self.bot.send_message(chat_id, 'Для начала работы выберите одну из следующих команд',
                              reply_markup=keyboard)

    @classmethod
    def clear_last_search(cls, callback: telebot.types.CallbackQuery):
        """
        Удаляет последний поиск у текущего пользователя.
        """
        cur_user = user.find_user(callback.message.chat.id)
        cur_user.clean_searches()
        user.save_users(cur_user)

    def ask_city(self, chat_id: int) -> None:
        """
        Спрашивает у пользователя город, в котором будет производиться поиск.
        Полученное от пользователя сообщение обрабатывается в функции get_city.
        Город предложенный в примере получается из функции random_city в файле cities_offer.
        :param chat_id: идентификационный номер чата, используемый для отправки сообщения.
        """
        random_city = cities_offer.random_city()
        ask_city = self.bot.send_message(chat_id, 'Введите интересующий вас'
                                                  f' город (пример: {random_city})')

        self.bot.register_next_step_handler(ask_city, self.get_city)

    def get_city(self, message: telebot.types.Message) -> None:
        """
        Сохраняет в переменную cache результат запроса, осуществленный в функции
        location_search в файле location_search.py.

        Если тип результата запроса str, значит это сообщение 'Что-то пошло не так. Попробуйте повторить запрос',
        которое отправляется пользователю, после чего снова запускается функция ask_city.

        В противном случае создается клавиатура с кнопками с полученными из запроса названиями городов, чтобы
        пользователь подтвердил выбор города.
        """
        self.cache = []
        result_list = location_search.location_search(message.text)

        if isinstance(result_list, str):
            self.bot.send_message(message.chat.id, result_list)
            self.cache = None
            self.ask_city(message.chat.id)
            return

        else:
            self.cache.append(result_list)
            keyboard = types.InlineKeyboardMarkup(row_width=1)
            button_names = [name for i_result in result_list for name, info in i_result.items()] + ['Другой город']
            button_calls = ['#city' + str(call_num) for call_num in range(len(button_names))]
            names_calls_dict = dict(zip(button_names, button_calls))
            self.cache.append(names_calls_dict)
            buttons = (types.InlineKeyboardButton(text=btn_name, callback_data=btn_call)
                       for btn_name, btn_call in self.cache[1].items())
            keyboard.add(*buttons)
            text = 'Выберите город из списка. Если нужного вам города нет, нажмите кнопку "Другой город"'
            self.bot.send_message(message.chat.id, text=text, reply_markup=keyboard)

    def save_city(self, call: str, chat_id: int) -> None:
        """
        Проверяет совпадения переменной call в списке в переменной cache, находит выбранный пользователем
        город и сохраняет его в поиск пользователя. Здесь же сохраняет время начала поиска.
        :param call: коллбэк с индексом города.
        :param chat_id: идентификационный номер чата, используемый для нахождения пользователя.
        """
        for i_name, i_call in self.cache[1].items():

            if call == i_call:
                result = i_name
                break

        for results in self.cache:
            for i_result in results:
                if result in i_result:
                    destination_name = result
                    destination_info = i_result[result]

                    cur_user = user.find_user(chat_id)
                    cur_search = user.Search()
                    cur_search.time_of_search = datetime.utcnow().strftime("%m/%d/%Y, %H:%M:%S")
                    cur_search.search_id_auto_setter()
                    cur_search.destination_name = destination_name
                    cur_search.destination_info = destination_info
                    cur_user.searches.append(cur_search)
                    user.save_users(cur_user)
                    self.cache = None
                    return

    def ask_date(self, chat_id: int, check_in: bool = False, check_out: bool = False) -> None:
        """
        Открывает календарь DetailedTelegramCalendar, в котором пользователь выбирает даты
        заселения в отель и дату последнего дня пребывания в отеле.
        :param chat_id: идентификационный номер чата, используемый для нахождения пользователя.
        :param check_in: флаг. Если True, то функция спрашивает дату заезда в отель.
        :param check_out: флаг. Если True, то функция спрашивает дату выезда из отеля.
        """
        if check_in:

            calendar, step = DetailedTelegramCalendar(min_date=date.today(),
                                                      max_date=date(2023, 12, 31),
                                                      locale='ru', calendar_id=1
                                                      ).build()
            self.bot.send_message(chat_id,
                                  f"Начало проживания в отеле: выберите {TSTEP[step]}",
                                  reply_markup=calendar)

        elif check_out:
            calendar, step = DetailedTelegramCalendar(min_date=self.cache[0] + timedelta(days=1),
                                                      max_date=date(2023, 12, 31),
                                                      locale='ru', calendar_id=2
                                                      ).build()
            self.bot.send_message(chat_id,
                                  f"Окончание проживания в отеле: выберите {TSTEP[step]}",
                                  reply_markup=calendar)

    def save_date(self, chat_id: int) -> None:
        """
        Сохраняет даты заезда и выезда из отеля в класс Search и удаляет данные
        из переменной cache.
        :param chat_id: идентификационный номер чата, используемый для нахождения пользователя.
        """
        check_in_date = self.cache[0]
        check_out_date = self.cache[1]

        dict_check_in = {'day': check_in_date.day,
                         'month': check_in_date.month,
                         'year': check_in_date.year}

        dict_check_out = {'day': check_out_date.day,
                          'month': check_out_date.month,
                          'year': check_out_date.year}

        cur_user = user.find_user(chat_id)
        cur_search = cur_user.searches.pop()

        cur_search.check_in = dict_check_in

        cur_search.check_out = dict_check_out

        cur_user.searches.append(cur_search)
        user.save_users(cur_user)

        self.cache = None

    def ask_rooms(self, chat_id: int) -> None:
        """
        Создает переменную с клавиатурой, созданной в функции rooms_kb в файле
        main_keyboard, чтобы спросить у пользователя количество бронируемых номеров.
        :param chat_id: идентификационный номер чата, используемый для отправки сообщения.
        """
        ask_rooms_keyboard = main_keyboard.rooms_kb()

        self.bot.send_message(chat_id, text='Выберите количество номеров, которое вы бы хотели забронировать',
                              reply_markup=ask_rooms_keyboard)

    def get_people(self, callback: telebot.types.CallbackQuery) -> None:
        """
        Запускает цикл for, который проходит по созданному списку из номеров (словарей).
        Если словарь пустой, то добавляет ключ adults и создает клавиатуру, чтобы пользователь указал кол-во взрослых, которые
        будут жить в номере.
        Если ключ adults есть, а children нет, то создает children и создает
        аналогичную adults клавиатуру для указания детей.
        Если оба ключа есть, то переходит к следующему номеру.
        Пройдя все номера, запускает функцию save_people для сохранения информации о проживающих
        в классе Search.
        """
        for i_index, i_room in enumerate(self.cache):

            all_adults = sum(map(lambda room_dict: room_dict.get('adults', 0), self.cache))
            all_children = sum(map(lambda room_dict: len(room_dict.get('children', [])), self.cache))
            all_people = all_adults + all_children
            max_people = 20 - all_people
            if max_people < 1:
                self.bot.send_message(callback.message.chat.id, 'Превышен лимит брони. Попробуйте ввод людей '
                                                                'сначала.')
                self.cache = None
                self.ask_rooms(callback.message.chat.id)
                return

            if 'adults' in i_room:
                if 'children' in i_room:
                    continue

                else:
                    if max_people > 6:
                        max_children = 6
                    else:
                        max_children = 6 - max_people
                    if max_children > 1:
                        children_width = max_children // 2
                    else:
                        children_width = 1
                    children_keyboard = types.InlineKeyboardMarkup(row_width=children_width)
                    children_buttons = (types.InlineKeyboardButton(
                        text=str(child),
                        callback_data=f'#room={i_index}@children={child}#')
                        for child in range(1, max_children + 1))

                    no_children = types.InlineKeyboardButton(text='Без детей',
                                                             callback_data=f'#room={i_index}@children=0#')

                    children_keyboard.add(no_children, *children_buttons)
                    self.bot.edit_message_text(f'Введите кол-во детей в номере {i_index + 1}',
                                               callback.message.chat.id,
                                               callback.message.message_id,
                                               reply_markup=children_keyboard)
                    return
            else:

                if max_people > 14:
                    max_adults = 14

                else:
                    max_adults = 14 - max_people

                if max_adults > 1:
                    adults_width = max_adults // 2

                else:
                    adults_width = 1
                adults_keyboard = types.InlineKeyboardMarkup(row_width=adults_width)
                adult_buttons = (types.InlineKeyboardButton(text=str(adult + 1),
                                                            callback_data=f'#room={i_index}@adults={adult + 1}#')
                                 for adult in range(max_adults))
                adults_keyboard.add(*adult_buttons)
                self.bot.edit_message_text(f'Введите кол-во взрослых в номере {i_index + 1}',
                                           callback.message.chat.id,
                                           callback.message.message_id,
                                           reply_markup=adults_keyboard)
                return

        else:
            self.save_people(callback)

    def get_children(self, children_amnt: int, cur_child: int, cur_room: int, callback: telebot.types.CallbackQuery):
        """"""
        keyboard = types.InlineKeyboardMarkup(row_width=6)
        buttons = (types.InlineKeyboardButton(text=f'{age}',
                                              callback_data=f'#age={age}#cur_child={cur_child}'
                                                            f'#total_children={children_amnt}#cur_room={cur_room}')
                   for age in range(18)
                   )
        keyboard.add(*buttons)
        ask_children = f'Введите возраст {cur_child}-ого ребенка'
        self.bot.edit_message_text(ask_children,
                                   callback.message.chat.id,
                                   callback.message.message_id,
                                   reply_markup=keyboard)

    def save_people(self, callback: telebot.types.CallbackQuery) -> None:
        """
        Сохраняет данные о проживающих в отеле в класс Search и запускает ask_hotels_amnt.
        """
        for i_room in self.cache:
            if len(i_room['children']) == 0:
                i_room.pop('children')

        cur_user = user.find_user(callback.message.chat.id)
        cur_search = cur_user.searches.pop()

        cur_search.people = self.cache
        cur_user.searches.append(cur_search)
        user.save_users(cur_user)
        self.cache = None
        self.ask_hotels_amnt(callback.message.chat.id)

    def ask_hotels_amnt(self, chat_id: int) -> None:
        """
        Сохраняет в переменную keyboard клавиатуру из функции hotels_kb в файле main_keyboard
        и отправляет в чат, чтобы пользователь указал количество загружаемых отелей.
        :param chat_id: идентификационный номер чата, используемый для отправки сообщения.
        """
        message_text = 'Введите количество отелей, которые вы хотите посмотреть'
        keyboard = main_keyboard.hotels_kb()
        self.bot.send_message(chat_id, text=message_text, reply_markup=keyboard)

    def ask_photos(self, chat_id: int) -> None:
        """
        Сохраняет в переменную keyboard клавиатуру, созданную в функции photos_kb в файле
        main_keyboard, и отправляет в чат, чтобы пользователь указал количество загружаемых
        фотографий отелей.
        :param chat_id: идентификационный номер чата, используемый для отправки сообщения.
        """
        message_text = 'Укажите количество загружаемых фото отелей'
        keyboard = main_keyboard.photos_kb()
        self.bot.send_message(chat_id, text=message_text, reply_markup=keyboard)

    def ask_commands(self, chat_id: int, again: bool = False) -> None:
        """
        Сохраняет в переменную keyboard клавиатуру с кнопками команд, созданную
        в функции option_choice_keyboard в файле main_keyboard.
        :param chat_id: идентификационный номер чата, используемый для отправки сообщения.
        :param again: флаг, меняющий клавиатуру, если True. Новая клавиатура будет иметь другие
        коллбэки.
        """
        keyboard = main_keyboard.option_choice_keyboard()
        if again:
            keyboard = main_keyboard.again_option_choice_keyboard()
        self.bot.send_message(chat_id, 'Выберите одну из следующих команд',
                              reply_markup=keyboard)

    def send_price_results(self, chat_id: int, search_results: List) -> None:
        """
        Создает цикл for, в котором формируются сообщения из результата запроса и отправляются в чат.
        :param chat_id: идентификационный номер чата, используемый для отправки сообщения.
        :param search_results: список с результатами запроса
        """

        if len(search_results) == 0:
            self.bot.send_message(chat_id, 'К сожалению, у вашего запроса не было результатов')

        else:

            for j_index, i_hotel in enumerate(search_results):
                name = f'{j_index + 1}. {i_hotel.name}'
                address = i_hotel.address
                price = i_hotel.price_per_night
                converted_price = get_converted_price(amount=price)

                if converted_price is None:

                    price = f'${i_hotel.price_per_night} за ночь\n'

                else:

                    price = converted_price

                    price = f'{price} руб. за ночь\n'

                distance = 'Расстояние до центра: {hotel_distance} км'.format(
                    hotel_distance=i_hotel.distance_from_destination)
                caption_text = '\n'.join([name, address, distance, price])

                photos = i_hotel.photos_url

                if len(photos) > 0:

                    media_group = []

                    for k_index, k_photo in enumerate(photos):

                        if k_index == 0:
                            prepared_photo = types.InputMediaPhoto(media=k_photo, caption=caption_text)

                        else:
                            prepared_photo = types.InputMediaPhoto(media=k_photo)

                        media_group.append(prepared_photo)

                    self.bot.send_media_group(chat_id, media_group)
                    time.sleep(2)

                else:
                    self.bot.send_message(chat_id, caption_text)

        self.ask_commands(chat_id, again=True)

    def ask_price_min(self, chat_id: int) -> None:
        """Спрашивает у пользователя минимальную цену отеля за ночь и отправляет ее в process_min"""
        ask_min = self.bot.send_message(chat_id, 'Введите цифрами минимальную цену отеля в рублях за ночь. '
                                                 'Пример: 5000')
        self.bot.register_next_step_handler(ask_min, self.process_min)

    def process_min(self, message: telebot.types.Message) -> None:
        """
        Проверяет минимальную цену отеля за ночь и если формат int, сохраняет ее
        в self.cache и запускает ask_price_max. Иначе запускает ask_price_min
        """
        user_min = message.text

        try:
            new_min = int(user_min)

        except ValueError:
            self.bot.send_message(message.chat.id, 'Неверный формат цены')
            self.ask_price_min(message.chat.id)
            return

        self.cache = {'min': new_min}

        self.ask_price_max(message.chat.id)

    def ask_price_max(self, chat_id: int) -> None:
        """Спрашивает у пользователя максимальную цену отеля за ночь и отправляет ее в proces_max"""
        ask_max = self.bot.send_message(chat_id, 'Введите цифрами максимальную цену отеля в рублях за ночь. '
                                                 'Пример: 10000')
        self.bot.register_next_step_handler(ask_max, self.proces_max)

    def proces_max(self, message: telebot.types.Message) -> None:
        """
        Проверяет максимальную цену отеля за ночь и если формат int и значение не меньше чем
        минимальная цена отеля, сохраняет ее self.cache и запускает save_prices и ask_min_distance.
        Иначе запускает снова ask_price_max.
        """
        user_max = message.text

        try:
            new_max = int(user_max)

            if new_max < self.cache['min']:
                raise TypeError

        except ValueError:
            self.bot.send_message(message.chat.id, 'Неверный формат цены')
            self.ask_price_max(message.chat.id)
            return

        except TypeError:
            self.bot.send_message(message.chat.id, 'Максимальная цена не может быть меньше минимальной')
            self.ask_price_max(message.chat.id)
            return

        self.cache['max'] = new_max

        self.save_prices(message.chat.id)

        self.ask_min_distance(message.chat.id)

    def save_prices(self, user_id: int) -> None:
        """Сохраняет данные о диапазоне цен пользователя."""
        cur_user = user.find_user(user_id)
        cur_search = cur_user.searches.pop()
        cur_search.price_range = self.cache
        self.cache = None
        cur_user.searches.append(cur_search)
        user.save_users(cur_user)

    def ask_min_distance(self, chat_id: int) -> None:
        """
        Спрашивает у пользователя минимальное расстояние отеля от центра города и отправляет
        его в обработку в proces_min_distance.
        """

        ask_min_distance = self.bot.send_message(chat_id, 'Введите цифрами минимальное расстояние удаленности'
                                                          ' отеля от центра города в километрах. Пример: 3.5')

        self.bot.register_next_step_handler(ask_min_distance, self.proces_min_distance)

    def proces_min_distance(self, message: telebot.types.Message) -> None:
        """
        Проверяет минимальное расстояние от отеля и если формат float, сохраняет
        данные в self.cache и запускает ask_max_distance. Иначе запускает ask_min_distance.
        """
        user_min_distance = message.text

        try:
            new_min_distance = float(user_min_distance)

        except ValueError:
            self.bot.send_message(message.chat.id, 'Неверный формат расстояния')
            self.ask_min_distance(message.chat.id)
            return

        distance = {'min_distance': new_min_distance}

        self.cache = distance

        self.ask_max_distance(message.chat.id)

    def ask_max_distance(self, chat_id: int) -> None:
        """
        Спрашивает у пользователя максимальное расстояние от отеля и отправляет его на
        обработку в proces_max_distance
        """
        ask_max_distance = self.bot.send_message(chat_id, 'Введите цифрами максимальное расстояние удаленности'
                                                          ' отеля от центра города в километрах. Пример: 4.5')

        self.bot.register_next_step_handler(ask_max_distance, self.proces_max_distance)

    def proces_max_distance(self, message: telebot.types.Message) -> None:
        """
        Проверяет максимальное расстояние отеля от центра и если формат float и значение не меньше чем
        минимальное расстояние, сохраняет его в self.cache, говорит пользователю, что
        поиск начался и запускает save_prices.
        Иначе запускает снова ask_max_distance.
        """
        user_max_distance = message.text

        try:
            new_max_distance = float(user_max_distance)
            if new_max_distance < self.cache['min_distance']:
                raise TypeError

        except ValueError:
            self.bot.send_message(message.chat.id, 'Неверный формат расстояния')
            self.ask_max_distance(message.chat.id)
            return

        except TypeError:
            self.bot.send_message(message.chat.id, 'Максимальное расстояние удаленности отеля от центра '
                                                   'не может быть меньше минимального')
            self.ask_max_distance(message.chat.id)
            return

        self.cache['max_distance'] = new_max_distance

        self.bot.send_message(message.chat.id, 'Начинаю поиск!')
        self.bot.send_message(message.chat.id, '\u23F3')

        self.save_distance(message.chat.id)

    def save_distance(self, user_id: int) -> None:
        """
        Сохраняет данные о желаемом пользователем расстоянии отеля от центра города.
        После обновляет данные текущего поиска через функцию best_deal в файле commands.py. Если
        результат этой функции - текст, то отправляет его сообщением пользователю.
        Иначе запускает send_price_results с обновленными данными.
        """
        cur_user = user.find_user(user_id)
        cur_search = cur_user.searches.pop()
        cur_search.distance_range = self.cache
        self.cache = None

        updated_search = commands.best_deal(cur_search)
        if isinstance(updated_search, str):

            user.save_users(cur_user)
            keyboard = main_keyboard.initial_keyboard()
            self.bot.send_message(user_id, updated_search, reply_markup=keyboard)
            return

        cur_user.searches.append(updated_search)
        user.save_users(cur_user)

        self.send_price_results(user_id, updated_search.results)
