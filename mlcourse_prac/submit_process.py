import io
import re
import shutil
import zipfile
from pathlib import Path
from typing import List

from mlcourse_prac.config import CONFIG
from mlcourse_prac.db import mlcourse_database
from mlcourse_prac.telebot import init_telebot


def get_solution_status_str(telegram_id: int) -> str:
    result = '*Статус очереди*\n'
    status = mlcourse_database.get_unchecked_solution_status(telegram_id)
    if status is None:
        result += 'У тебя нет непроверенных решений.'
    elif status == 'new':
        result += 'Загруженное решение пока в очереди на проверку.'
    else:
        result += 'Загруженное решение проверяется прямо сейчас!'
    return result


def get_task_status(telegram_id: int, task: str = 'badnets') -> str:
    task_pretty = 'Первая' if task == 'badnets' else 'Вторая'
    result = f'*{task_pretty} часть задания*\n'

    result += 'Последнее решение: '
    last_solution = mlcourse_database.get_top_solution(telegram_id, task, 'latest')
    if last_solution is None:
        result += 'отсутствует'
    else:
        time_sent, clean, poisoned = last_solution
        result += (
            f'{poisoned:.4f} с атакой, {clean:.4f} без атаки, отправлено '
            + time_sent.strftime('%d.%m в %H:%M')
        )

    result += '\nЛучшее решение: '
    best_solution = mlcourse_database.get_top_solution(telegram_id, task, 'best')
    if best_solution is None:
        result += 'отсутствует'
    else:
        time_sent, clean, poisoned = best_solution
        result += (
            f'{poisoned:.4f} с атакой, {clean:.4f} без атаки, отправлено '
            + time_sent.strftime('%d.%m в %H:%M')
        )
    return result


def submit_process():
    bot, markup = init_telebot()

    @bot.message_handler(commands=['start'])
    def handle_start(message):
        bot.send_message(
            message.chat.id,
            'Привет, {0.first_name}! Введи: Фамилию Имя Отчество'.format(message.from_user),
        )
        bot.register_next_step_handler(message, handle_full_name)

    def handle_full_name(message):
        name_parts: List[str] = message.text.lower().split(' ')
        if len(name_parts) not in [3, 2]:
            bot.reply_to(message, 'В ФИО должны быть 3 или 2 слова!')
            return

        all_russian = all([re.match('[а-яё]+', name_part) for name_part in name_parts])
        if not all_russian:
            bot.reply_to(message, 'В ФИО должны быть только русские буквы!')
            return

        full_name = ' '.join([name_part.capitalize() for name_part in name_parts])
        mlcourse_database.set_student_full_name(message.chat.id, full_name)

        bot.send_message(message.chat.id, 'Теперь введи номер студенческого')
        bot.register_next_step_handler(message, handle_student_id)

    def handle_student_id(message):
        try:
            student_id = int(message.text)
        except ValueError:
            bot.reply_to(message, 'Номер студенческого должен быть целым числом!')
            return

        mlcourse_database.set_student_id(message.chat.id, student_id)
        bot.send_message(message.chat.id, 'Теперь можно загружать zip-архив с решением')

    @bot.message_handler(content_types=['document'])
    def handle_solution(message):
        student_info = mlcourse_database.get_student_info(message.chat.id)
        if student_info is None or student_info[1] is None:
            bot.reply_to(message, 'Необходимо пройти регистрацию, введи команду: /start')
            return

        file_info = bot.get_file(message.document.file_id)
        max_solution_size_mb = int(CONFIG['telebot']['max_solution_size_mb'])
        if file_info.file_size is None or file_info.file_size > max_solution_size_mb * (2**20):
            bot.reply_to(message, f'Превышен максимальный размер файлов {max_solution_size_mb} MB!')
            return

        downloaded_file: bytes = bot.download_file(file_info.file_path)
        try:
            zf = zipfile.ZipFile(io.BytesIO(downloaded_file))
            zf_members = zf.namelist()
        except zipfile.BadZipFile:
            bot.reply_to(message, 'Файл не является корректным zip-архивом!')
            return

        for required_file in ['requirements.txt', 'solution.py']:
            if required_file not in zf_members:
                bot.reply_to(message, 'В архиве должны быть файлы requirements.txt и solution.py!')
                return

        uncompressed_path = Path('/solutions') / str(message.chat.id)
        if uncompressed_path.exists():
            shutil.rmtree(uncompressed_path)
        zf.extractall(uncompressed_path)
        zf.close()

        mlcourse_database.submit_solution(message.chat.id)
        bot.reply_to(message, 'Решение принято! Напишу по окончании проверки :)')

    @bot.message_handler(commands=['status'])
    def handler_status(message):
        student_info = mlcourse_database.get_student_info(message.chat.id)
        if student_info is None or student_info[1] is None:
            bot.reply_to(message, 'Необходимо пройти регистрацию, введи команду: /start')
            return

        response = (
            get_solution_status_str(message.chat.id)
            + '\n\n'
            + get_task_status(message.chat.id, 'badnets')
            + '\n\n'
            + get_task_status(message.chat.id, 'lira')
        )
        bot.send_message(message.chat.id, response, reply_markup=markup, parse_mode='Markdown')

    bot.infinity_polling()
