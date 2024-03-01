from typing import Tuple

from telebot import TeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from mlcourse_prac.config import CONFIG


def init_telebot() -> Tuple[TeleBot, InlineKeyboardMarkup]:
    bot = TeleBot(CONFIG['telebot']['token'])
    button = InlineKeyboardButton(
        'MLCourse Leaderboard', url='https://mlcourse.at.ispras.ru/leaderboard'
    )
    markup = InlineKeyboardMarkup()
    markup.add(button)

    return bot, markup
