import config
from telegram_hotels_bot.bot import my_bot
import telebot
from telebot import apihelper
import sys


"""Файл main. Служит для запуска бота, написанного в классе Bot в файле my_bot.py"""
if __name__ == '__main__':
    try:
        if config.check_config():
            print('Bot is now active')
            bot = my_bot.MyBot()
            bot.start()
        else:
            raise Exception('Bad config data')
    except Exception as exc:
        print(exc)
        sys.exit(1)





