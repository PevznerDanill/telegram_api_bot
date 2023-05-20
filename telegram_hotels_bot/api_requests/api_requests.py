import requests
import logging
import os
from typing import Dict
import json
from telegram_hotels_bot import config

"""Файл с запросами к Hotel Api"""
log_path = os.path.join('api_requests/', 'logg_requests.log')

logging.basicConfig(
        filename=log_path,
        level=logging.ERROR,
        filemode='a',
        format="%(asctime)s - %(levelname)s - %(message)s")


def get_request(url: str, headers: Dict[str, str], querystring: Dict[str, str]) -> Dict:
    """Отправляет запрос с тегом GET"""
    result = None

    try:
        response = requests.request("GET", url=url, headers=headers, params=querystring)
        result = response.json()
        if 'errors' in result.keys() or result is None:
            raise ValueError

    except requests.Timeout as time_end:
        logging.error(time_end)

    except requests.RequestException as exc:
        logging.error(exc)

    except ValueError:
        result = get_request(url, headers, querystring)
        return result

    return result


def post_request(url: str, payload: Dict[str, str], headers: Dict[str, str]) -> Dict:
    """Отправляет запрос с тегом POST"""
    result = None

    try:
        response = requests.request("POST", url=url, json=payload, headers=headers)

        result = response.json()

    except requests.Timeout as time_end:
        logging.error(time_end)

    except requests.RequestException as exc:
        logging.error(exc)

    return result


def get_converted_price(amount):
    """Отправляет запрос для конвертации цены"""
    url = f"https://api.apilayer.com/currency_data/convert?to=RUB&from=USD&amount={amount}"

    payload = {}

    headers = {
        "apikey": config.api_key_for_currency
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    status_code = response.status_code
    if status_code == 200:
        result = json.loads(response.text)
        return round(result.get('result'), 2)
    return None
