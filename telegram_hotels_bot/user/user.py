import pickle
from typing import List, Optional, Dict
from datetime import datetime
from telegram_hotels_bot.api_requests.api_requests import get_converted_price
import re
"""Файл с классами User, Search и Hotel"""


class User:
    """
    Класс User. Хранит в своих переменных данные о пользователе
    Arguments:
        self._user_id (int): идентификационный номер пользователя.
        self._firstname (str): имя пользователя.
        self._lastname (str): фамилия пользователя.
        self._username (str): никнейм пользователя.
        self._searches (List[Search]): поиски пользователя.
    """
    def __init__(self, user_id: Optional[int] = None, firstname: Optional[str] = None,
                 lastname: Optional[str] = None, username: Optional[str] = None):
        self._user_id = user_id
        self._firstname = firstname
        self._lastname = lastname
        self._username = username
        self._searches = []

    def __str__(self):
        return 'user_id: {user_id}\nfirstname: {firstname}\n' \
               'lastname: {lastname}\nusername: {username}\nsearches: {searches}'.format(
                user_id=self.user_id,
                firstname=self.firstname,
                lastname=self.lastname,
                username=self.username,
                searches=self.searches
                )

    @property
    def user_id(self) -> int:
        """Геттер для идентификационного номера пользователя"""
        return self._user_id

    @property
    def firstname(self) -> str:
        """Геттер для имени пользователя"""
        return self._firstname

    @property
    def lastname(self) -> str:
        """Геттер для фамилии пользователя"""
        return self._lastname

    @property
    def username(self) -> str:
        """Геттер для никнейма пользователя"""
        return self._username

    @property
    def searches(self) -> List['Search']:
        """Геттер для списка поисков пользователя"""
        return self._searches

    @user_id.setter
    def user_id(self, new_id: int) -> None:
        """Сеттер для идентификационного номера пользователя """
        self._user_id = new_id

    @firstname.setter
    def firstname(self, new_firstname: str) -> None:
        """Сеттер для имени пользователя """
        self._firstname = new_firstname

    @lastname.setter
    def lastname(self, new_lastname: str) -> None:
        """Сеттер для фамилии пользователя """
        self._lastname = new_lastname

    @username.setter
    def username(self, new_username: str) -> None:
        """Сеттер для никнейма пользователя """
        self._username = new_username

    @searches.setter
    def searches(self, new_searches: List['Search']) -> None:
        self._searches = new_searches

    def clean_searches(self) -> None:
        """Удаляет поиски"""
        self._searches = []


class Search:
    """
    Класс Search. Хранит переменные для создания запросов к Hotels Api.
    Arguments:
        destination_name (str): полное название города, в котором производится поиск.
        destination_info (Dict): информация о расположении города.
        time_of_search (str): время поиска.
        check_in (Dict): дата заезда в отель.
        check_out (Dict): дата последнего дня в отеле.
        people (List): данные о проживающих.
        max_items (int): количество загружаемых результатов запроса.
        type_of_search (str): тип выбранной команды.
    """

    def __init__(self, destination_name=None, destination_info=None, time_of_search=None, check_in=None,
                 check_out=None, people=None, max_items=None, type_of_search=None, price_range=None,
                 distance_range=None, photos_amnt=None):

        self._destination_name = destination_name
        self._destination_info = destination_info
        self._time_of_search = time_of_search
        self._check_in = check_in
        self._check_out = check_out
        self._people = people
        self._max_items = max_items
        self._type_of_search = type_of_search
        self._price_range = price_range
        self._distance_range = distance_range
        self._photos_amnt = photos_amnt
        self._results: List['Hotel'] = []
        self._favorite_hotel: Optional['Hotel'] = None
        self._search_id = None

    def __str__(self):
        if len(self.results) > 0:
            results = '\n'.join([f'{hotel_str}' for hotel_str in self.results])

        else:
            results = ''

        return '\nНомер поиска: {search_id}\nВремя поиска (UTC): {time_of_search}\n' \
               'Место поиска: {destination_name}\n' \
               'Даты заезда: {check_in_d}/{check_in_m}/{check_in_y}\n' \
               'Дата выезда: {check_out_d}/{check_out_m}/{check_out_y}\n' \
               'Тип поиска: {type_of_search}\n' \
               'Найденные отели:\n{results}'.format(
                search_id=self._search_id,
                destination_name=self.destination_name,
                check_in_d=self.check_in['day'],
                check_in_m=self.check_in['month'],
                check_in_y=self.check_in['year'],
                check_out_d=self.check_out['day'],
                check_out_m=self.check_out['month'],
                check_out_y=self.check_out['year'],
                time_of_search=self.time_of_search,
                results=results,
                type_of_search=self.type_of_search
                )

    @property
    def destination_name(self) -> str:
        """Геттер для полного названия города, в котором производится поиск."""
        return self._destination_name

    @property
    def search_id(self):
        return self._search_id

    @property
    def destination_info(self) -> Dict[str, Dict[str, float]]:
        """Геттер для информации о городе, в котором производится поиск."""
        return self._destination_info

    @property
    def time_of_search(self) -> str:
        """Геттер для времени поиска"""
        return self._time_of_search

    @property
    def check_in(self) -> Dict[str, int]:
        """Геттер для даты заезда в отель"""
        return self._check_in

    @property
    def check_out(self) -> Dict[str, int]:
        """Геттер для даты последнего дня в отеле"""
        return self._check_out

    @property
    def people(self) -> List[Dict[str, int]]:
        """Геттер для данных о проживающих в отеле"""
        return self._people

    @property
    def max_items(self) -> int:
        """Геттер для количества загружаемых в чат результатах"""
        return self._max_items

    @property
    def type_of_search(self) -> str:
        """Геттер для названия выбранной команды"""
        return self._type_of_search

    @property
    def price_range(self) -> Dict[str, int]:
        """Геттер для диапазона цен"""
        return self._price_range

    @property
    def distance_range(self) -> Dict[str, float]:
        """Геттер для диапазона расстояния"""
        return self._distance_range

    @property
    def results(self) -> List['Hotel']:
        """Геттер для результатов поиска"""
        return self._results

    @property
    def favorite_hotel(self) -> 'Hotel':
        """Геттер для выбранного пользователем отеля"""
        return self._favorite_hotel

    @property
    def photos_amnt(self) -> int:
        """Геттер для количества фото"""
        return self._photos_amnt

    @destination_name.setter
    def destination_name(self, new_destination: str) -> None:
        """Сеттер для полного названия города, в котором производится поиск."""
        self._destination_name = new_destination

    @destination_info.setter
    def destination_info(self, new_destination_info: Dict[str, Dict[str, float]]) -> None:
        """Сеттер для информации о городе, в котором производится поиск."""
        self._destination_info = new_destination_info

    @time_of_search.setter
    def time_of_search(self, new_time_of_search: str) -> None:
        """Сеттер для времени поиска"""
        self._time_of_search = new_time_of_search

    def search_id_auto_setter(self) -> None:
        """Сеттер для идентификационного номера поиска"""
        cur_time = datetime.utcnow()
        new_id = f'{cur_time.hour}{cur_time.microsecond}'
        self._search_id = new_id

    @check_in.setter
    def check_in(self, new_check_in: Dict[str, int]) -> None:
        """Сеттер для даты заезда в отель"""
        self._check_in = new_check_in

    @check_out.setter
    def check_out(self, new_check_out: Dict[str, int]) -> None:
        """Сеттер для даты последнего дня в отеле."""
        self._check_out = new_check_out

    @people.setter
    def people(self, new_people: List[Dict[str, int]]) -> None:
        """Сеттер для данных о проживающих в отеле."""
        self._people = new_people

    @max_items.setter
    def max_items(self, new_max_items: int) -> None:
        """Сеттер для количества загружаемых результатов."""
        self._max_items = new_max_items

    @type_of_search.setter
    def type_of_search(self, new_type: str) -> None:
        """Сеттер для типа команды."""
        self._type_of_search = new_type

    @price_range.setter
    def price_range(self, new_range: Dict[str, int]) -> None:
        """Сеттер для диапазона цен."""
        self._price_range = new_range

    @distance_range.setter
    def distance_range(self, new_distance_range: Dict[str, float]) -> None:
        """Сеттер для диапазона расстояния"""
        self._distance_range = new_distance_range

    @results.setter
    def results(self, new_results: List['Hotel']) -> None:
        """Сеттер для результатов поиска"""
        self._results = new_results

    @favorite_hotel.setter
    def favorite_hotel(self, new_hotel: 'Hotel') -> None:
        """Сеттер для выбранного пользователем отеля"""
        self._favorite_hotel = new_hotel

    @photos_amnt.setter
    def photos_amnt(self, new_photos_amnt: int) -> None:
        """Сеттер для количества фото отеля"""
        self._photos_amnt = new_photos_amnt

    def update_search(self):
        new_search = Search(destination_name=self.destination_name,
                            destination_info=self.destination_info,
                            check_in=self.check_in,
                            check_out=self.check_out,
                            people=self.people,
                            max_items=self.max_items,
                            time_of_search=datetime.utcnow().strftime("%m/%d/%Y, %H:%M:%S"),
                            photos_amnt=self.photos_amnt
                            )
        new_search.search_id_auto_setter()
        return new_search


class Hotel:
    """
    Класс Hotel. Служит для хранения переменных с данными об отеле.
    Arguments:
        name (str): название отеля.
        hotel_id (str): идентификационный номер отеля.
        price_per_night (float): цена отеля за ночь.
        distance_from_destination (float): расстояние до центра.
    """
    def __init__(self, name=None, hotel_id=None, price_per_night=None, distance_from_destination=None): #total_price=None):
        self._name = name
        self._hotel_id = hotel_id
        self._price_per_night = price_per_night
        self._distance_from_destination = distance_from_destination
        self._address: Optional[str] = None
        self._photos_url: Optional[List[Dict[str, str]]] = None

    def __str__(self):

        price = self._price_per_night
        converted_price = get_converted_price(price)
        if converted_price:
            result_text = '{hotel_name}: {hotel_price} руб. за ночь'.format(
            hotel_name=self.name,
            hotel_price=converted_price
        )
        else:
            result_text = '{hotel_name}: ${hotel_price} за ночь'.format(
                hotel_name=self.name,
                hotel_price=price
            )

        return result_text

    @property
    def name(self) -> str:
        """Геттер для названия отеля."""
        return self._name

    @property
    def hotel_id(self) -> str:
        """Геттер для идентификационного номера отеля."""
        return self._hotel_id

    @property
    def price_per_night(self) -> float:
        """Геттер для цены отеля за ночь."""
        return self._price_per_night

    @property
    def address(self) -> str:
        """Геттер для адреса отеля."""
        return self._address

    @property
    def photos_url(self) -> List[Dict[str, str]]:
        """Геттер для списка словарей со ссылками фото."""
        return self._photos_url

    @property
    def distance_from_destination(self) -> float:
        """Геттер для расстояния от отеля до центра города."""
        return self._distance_from_destination

    @name.setter
    def name(self, new_name: str) -> None:
        """Сеттер для полного названия отеля."""
        self._name = new_name

    @hotel_id.setter
    def hotel_id(self, new_id: str) -> None:
        """Сеттер для идентификационного номера отеля"""
        self._hotel_id = new_id

    @price_per_night.setter
    def price_per_night(self, new_price: float) -> None:
        """Сеттер для цены отеля за ночь."""

        self._price_per_night = new_price

    @address.setter
    def address(self, new_address: str) -> None:
        """Сеттер для адреса отеля."""
        self._address = new_address

    @photos_url.setter
    def photos_url(self, new_photos: List[Dict[str, str]]) -> None:
        """Сеттер для списка словарей со ссылками фото."""
        self._photos_url = new_photos

    @distance_from_destination.setter
    def distance_from_destination(self, new_distance: float) -> None:
        """Сеттер для расстояния от отеля до центра города"""
        self._distance_from_destination = new_distance


def hotels_from_dict(hotels_dict: Dict[str, int]) -> List['Hotel']:
    """
    Формирует список с объектами класса Hotel из словаря с именем и идентификационным
    номером отеля.
    """
    hotels = []
    for i_name, i_id in hotels_dict.items():
        i_id = str(i_id)
        new_hotel = Hotel(name=i_name, hotel_id=i_id)
        hotels.append(new_hotel)

    return hotels


def find_user(user_id: int) -> 'User':
    """Находит текущего пользователя по его идентификационному номеру."""
    with open('history.pickle', 'rb') as history:
        users = pickle.load(history)

    return users.get(user_id, None)


def save_users(user: 'User') -> None:
    """Сохраняет данные текущего пользователя в формате pickle."""
    with open('history.pickle', 'rb') as history:
        users = pickle.load(history)

    for user_id, i_user in users.items():
        if user_id == user.user_id:
            users[user_id] = user

    with open('history.pickle', 'wb') as history:
        pickle.dump(users, history)


