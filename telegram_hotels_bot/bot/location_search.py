from telegram_hotels_bot.api_requests import api_requests
from telegram_hotels_bot import config


def location_search(city_name):

    url = "https://hotels4.p.rapidapi.com/locations/v3/search"

    querystring = {"q": city_name, "locale": "ru_RU"}

    headers = {
        "X-RapidAPI-Key": config.rapidAPI_key,
        "X-RapidAPI-Host": "hotels4.p.rapidapi.com"
    }

    data = api_requests.get_request(url=url, querystring=querystring, headers=headers)

    if (data is None) or ('errors' in data.keys()):
        return 'Что-то пошло не так. Попробуйте повторить запрос'

    data = data.get('sr')

    found_destinations = []

    for i_result in data:
        if i_result['type'] == 'CITY':
            names = i_result['regionNames']
            full_name = names['fullName']
            lat = float(i_result['coordinates']['lat'])
            long = float(i_result['coordinates']['long'])
            region_id = i_result['gaiaId']
            destination_info = {full_name: {'coordinates': {'latitude': lat, 'longitude': long},
                                            'regionId': region_id}}
            found_destinations.append(destination_info)

    return found_destinations




