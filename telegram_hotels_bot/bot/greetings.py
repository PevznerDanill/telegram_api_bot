import re
import requests
import bs4
import telebot
import os
import string
import pickle
from telegram_hotels_bot.user import user


"""
Файл с функциями для проверки сообщения на приветствие, формирование нового сообщения для отправки
и сохранения данных о пользователе в файле history.pickle.
"""


def greetings(message: telebot.types.Message) -> bool:
    """Проверяет сообщение, если находит в нем приветствие"""

    my_message = message.text.lower()

    no_doubles = ''.join(((sym for ind, sym in enumerate(my_message)
              if (ind + 1) != len(my_message) and sym != my_message[ind + 1]))) + my_message[-1]

    clean_message = re.sub(rf'[{string.punctuation}]', '', no_doubles)

    if check_synonyms(clean_message):
        return True

    return False


def check_synonyms(greeting_word: str) -> bool:
    """Проверяет, есть ли приветственное сообщение в списке синонимов к слову привет из wiktionary"""
    url = 'https://ru.wiktionary.org/wiki/%D0%BF%D1%80%D0%B8%D0%B2%D0%B5%D1%82'
    my_req = requests.get(url)
    soup = bs4.BeautifulSoup(my_req.text, 'lxml')

    synonyms = [item.text for item in soup.find(class_='mw-parser-output').find_all('ol')[1].find_all('a')
                if not item.text.endswith('.')]

    synonyms += ['привет', 'здорово']

    for i_synonym in synonyms:

        pattern = rf'{i_synonym}'
        if re.search(pattern, greeting_word):
            return True

    return False


def say_hi_and_remember(message: telebot.types.Message) -> str:
    """
    Смотрит историю пользователей, проверяя, есть ли там данные о текущем пользователе.
    Формирует сообщение для ответного приветствия.
    """
    path = os.path.abspath(os.path.join(os.path.curdir, 'history.pickle'))
    history = open(path, 'rb')
    all_users = pickle.load(history)
    history.close()
    if (len(all_users.keys()) < 1) or (message.from_user.id not in all_users):
        user_id = message.from_user.id
        firstname = message.from_user.first_name
        lastname = message.from_user.last_name
        username = message.from_user.username
        new_user = user.User(user_id=user_id, firstname=firstname, lastname=lastname, username=username)
        all_users[new_user.user_id] = new_user

        with open('history.pickle', 'wb') as history:
            pickle.dump(all_users, history)
        return f'Здравствуйте, {new_user.firstname}!'

    else:

        for user_id, i_user in all_users.items():
            if user_id == message.from_user.id:
                return f'Рады вас снова видеть, {i_user.firstname}!'
