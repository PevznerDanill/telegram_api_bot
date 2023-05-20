from telegram_hotels_bot.user import user
from datetime import datetime, timedelta
from telegram_hotels_bot.api_requests import api_requests
from typing import List, Dict, Optional, Union
from telegram_hotels_bot import config





def price_list(cur_search: 'Search', low_price=False, high_price=False) -> Optional[Union[List['Hotel'], str]]:
    """
    Создает параметры для запросов в Hotel Api, в результате которых получается список отелей
    Также сохраняет тип поиска.
    """

    destination = cur_search.destination_info
    check_in = cur_search.check_in
    check_out = cur_search.check_out
    people = cur_search.people
    result_index = 0

    if low_price:
        max_items = cur_search.max_items

    else:
        max_items = 200

    try:
        data = get_properties_list_data(
            destination=destination, check_in=check_in, check_out=check_out,
            people=people, result_index=result_index, max_items=max_items, high=True
        )

        if data is None or 'errors' in data.keys():
            raise ValueError

    except ValueError:
        return 'Что-то пошло не так. Пожалуйста, повторите запрос'

    if low_price:
        cur_search = save_name_id_price(data, cur_search, low_price=True)

    elif high_price:
        cur_search = save_name_id_price(data, cur_search, high_price=True)

    if isinstance(cur_search, str):
        return cur_search

    cur_search = get_address_and_photos(cur_search)

    return cur_search


def get_properties_list_data(destination, check_in, check_out, people, result_index, max_items, high=False, low=False):
    """Создает данные для запроса списка отелей"""
    url = "https://hotels4.p.rapidapi.com/properties/v2/list"

    payload = {
        "currency": "USD",

        "locale": "ru_RU",

        "destination": destination,
        "checkInDate": {
            "day": check_in['day'],
            "month": check_in['month'],
            "year": check_in['year']
        },
        "checkOutDate": {
            "day": check_out['day'],
            "month": check_out['month'],
            "year": check_out['year']
        },
        "rooms": people,

        "resultsStartingIndex": result_index,
        "resultsSize": max_items,
        "sort": "PRICE_LOW_TO_HIGH",
        "filters": {
            "availableFilter": "SHOW_AVAILABLE_ONLY"
        }

    }
    headers = {
        "content-type": "application/json",
        "X-RapidAPI-Key": config.rapidAPI_key,
        "X-RapidAPI-Host": "hotels4.p.rapidapi.com"
    }

    data = api_requests.post_request(url=url, payload=payload, headers=headers)
    return data


def save_name_id_price(data: Dict, cur_search: 'Search', low_price=False, high_price=False) -> 'Search':
    """Обновляет данные текущего поиска, добавляя в него цену и идентификационный номер отеля"""
    cur_search.results = []
    destination = cur_search.destination_info
    check_in = cur_search.check_in
    check_out = cur_search.check_out
    people = cur_search.people
    max_items = cur_search.max_items
    data = data.get('data').get('propertySearch').get('properties')

    if high_price:
        result_index = 0
        data_amnt = len(data)
        while data_amnt == 200:
            result_index += 199
            data = get_properties_list_data(
                destination=destination, check_in=check_in, check_out=check_out,
                people=people, result_index=result_index, max_items=200
            )

            count = 0
            while data is None or 'errors' in data.keys():
                data = get_properties_list_data(
                    destination=destination, check_in=check_in, check_out=check_out,
                    people=people, result_index=result_index, max_items=200
                )
                count += 1
                if count > 5:
                    return 'Что-то пошло не так. Попробуйте повторить запрос'

            data = data.get('data').get('propertySearch').get('properties')
            data_amnt = len(data)

        data = data[::-1]

    for i_index, i_data in enumerate(data):

        if i_index + 1 > max_items:
            break

        else:
            hotel_name = i_data['name']
            hotel_id = i_data['id']

            price = round(float(i_data['price']['lead']['amount']), 2)

            distance_from_destination = float(i_data['destinationInfo']['distanceFromDestination']['value'])

            new_hotel = user.Hotel(name=hotel_name, hotel_id=hotel_id,
                                   price_per_night=price, distance_from_destination=distance_from_destination)
            cur_search.results.append(new_hotel)

    return cur_search


def get_address_and_photos(cur_search: 'Search') -> 'Search':
    """Обновляет данные текущего поиска, добавляя в него адреса и фото отелей"""
    for i_hotel in cur_search.results:
        url = "https://hotels4.p.rapidapi.com/properties/v2/detail"

        payload = {
            "currency": "USD",
            "locale": "ru_RU",
            "propertyId": i_hotel.hotel_id
        }

        headers = {
            "content-type": "application/json",
            "X-RapidAPI-Key": config.rapidAPI_key,
            "X-RapidAPI-Host": "hotels4.p.rapidapi.com"
        }

        data = api_requests.post_request(url=url, payload=payload, headers=headers)
        count = 0
        while data is None or 'errors' in data.keys():
            data = api_requests.post_request(url=url, payload=payload, headers=headers)
            count += 1
            if count > 5:
                return 'Что-то пошло не так. Попробуйте повторить запрос'

        address_dict = data['data']['propertyInfo']['summary']['location']['address']
        address_line = address_dict['addressLine']
        i_hotel.address = address_line
        data = enumerate(data['data']['propertyInfo']['propertyGallery']['images'])
        i_hotel.photos_url = []

        for i_index, i_data in data:
            if (cur_search.photos_amnt < 1) or (i_index + 1 > cur_search.photos_amnt):
                break

            image_dict = i_data['image']

            i_hotel.photos_url.append(image_dict['url'])

    return cur_search


def days(check_in: str, check_out: str) -> int:
    """
    Считает общее кол-во дней пребывания
    """
    check_in_date = datetime.strptime(check_in, '%Y-%m-%d')
    check_out_date = datetime.strptime(check_out, '%Y-%m-%d')

    return (check_out_date - check_in_date).days


def give_history(user_id: int) -> str:
    """
    Формирует сообщение с результатами последних пяти поисков
    """
    cur_user = user.find_user(user_id)
    if len(cur_user.searches) > 0:
        for i_search in cur_user.searches:
            if len(i_search.results) < 1:
                cur_user.searches.remove(i_search)

        cur_user.searches = cur_user.searches[:5]


        message_text = '\n'.join([f'{search}' for search in cur_user.searches])

        user.save_users(cur_user)

        return message_text

    return 'Пока что история поисков пуста'


def best_deal(cur_search):
    """
    Сохраняет данные из запроса для настраиваемого поиска
    """
    data = get_best_deal_data(cur_search)
    if isinstance(data, str):
        return data

    max_price = cur_search.price_range['max']
    min_price = cur_search.price_range['min']
    max_distance = cur_search.distance_range['max_distance']
    min_distance = cur_search.distance_range['min_distance']

    name_id_price_distance = []

    for i_data in data:
        hotel_name = i_data['name']
        hotel_id = i_data['id']
        price = float(i_data['price']['lead']['amount'])
        distance = float(i_data['destinationInfo']['distanceFromDestination']['value'])
        new_hotel = {'name': hotel_name, 'id': hotel_id,
                     'price': price, 'distance': distance}
        name_id_price_distance.append(new_hotel)

    filter_price = list(filter(lambda hotel: min_price < hotel['price'] < max_price, name_id_price_distance))
    filtered_list = list(filter(lambda hotel: min_distance < hotel['distance'] < max_distance, filter_price))

    cur_search.results = [user.Hotel(name=i_hotel['name'], hotel_id=i_hotel['id'],
                                     price_per_night=i_hotel['price'], distance_from_destination=i_hotel['distance'])
                          for i_index, i_hotel in enumerate(filtered_list) if (i_index + 1) < cur_search.max_items]

    cur_search = get_address_and_photos(cur_search)

    return cur_search


def get_best_deal_data(cur_search):
    """
    Формирует данные для запроса для настраиваемого поиска
    """
    destination_info = cur_search.destination_info
    check_in = cur_search.check_in
    check_out = cur_search.check_out
    people = cur_search.people
    price_range = cur_search.price_range

    url = "https://hotels4.p.rapidapi.com/properties/v2/list"

    payload = {
        "currency": "USD",

        "locale": "ru_RU",

        "destination": destination_info,
        "checkInDate": {
            "day": check_in['day'],
            "month": check_in['month'],
            "year": check_in['year']
        },
        "checkOutDate": {
            "day": check_out['day'],
            "month": check_out['month'],
            "year": check_out['year']
        },
        "rooms": people,

        "resultsStartingIndex": 0,
        "resultsSize": 200,
        "sort": "DISTANCE",
        "filters": {

            "availableFilter": "SHOW_AVAILABLE_ONLY",
            'price': price_range
        }

    }
    headers = {
        "content-type": "application/json",
        "X-RapidAPI-Key": config.rapidAPI_key,
        "X-RapidAPI-Host": "hotels4.p.rapidapi.com"
    }

    data = api_requests.post_request(url=url, headers=headers, payload=payload)

    try:
        data = data.get('data').get('propertySearch').get('properties')

    except AttributeError:
        data = api_requests.post_request(url=url, headers=headers, payload=payload)

        data = data.get('data', 0)
        if data is None:
            data = 'Что-то пошло не так, попробуйте начать поиск с начала'

    return data
