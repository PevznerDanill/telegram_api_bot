import bs4
import requests
import random
import re
import string


page = random.randint(1, 100)

url = f'https://www.unipage.net/ru/cities?page={page}&per-page=100'

response = requests.get(url)

data = response.text

soup = bs4.BeautifulSoup(data, 'lxml')

divs = soup.find_all('div', {'class': 'generated-card-header__row'})

foreign_cities = [div.text.split(', ')[1] for div in divs]


def random_city():
    if len(foreign_cities) > 0:
        return random.choice(foreign_cities)
    return 'Малага'
