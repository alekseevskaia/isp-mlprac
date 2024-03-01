import shutil
import subprocess
import time
from pathlib import Path

from mlcourse_prac.config import CONFIG
from mlcourse_prac.db import mlcourse_database
from mlcourse_prac.leaderboard import update_leaderboard
from mlcourse_prac.telebot import init_telebot


def check_process():
    bot, _ = init_telebot()

    while True:
        oldest_new_solution = mlcourse_database.pull_oldest_new_solution()
        if oldest_new_solution is None:
            time.sleep(int(CONFIG['evaluation']['sleep_no_solutions_minutes']) * 60)
            continue

        telegram_id = oldest_new_solution[0]
        all_solutions_dir = Path('/solutions')
        original_dir = all_solutions_dir / str(telegram_id)
        evaluation_dir = all_solutions_dir / 'evaluation' / str(telegram_id)
        shutil.copytree(original_dir, evaluation_dir)

        shell_script_path = Path(__file__).resolve().parent / 'venv.sh'
        shutil.copy(shell_script_path, evaluation_dir)

        run_timeout_minutes = int(CONFIG['evaluation']['run_timeout_minutes'])
        try:
            completed = subprocess.run(
                ['/bin/bash', 'venv.sh'],
                capture_output=True,
                text=True,
                timeout=run_timeout_minutes * 60,
                cwd=evaluation_dir,
            )
        except subprocess.TimeoutExpired:
            mlcourse_database.set_error_status(telegram_id)
            bot.send_message(
                telegram_id,
                (
                    'Последнее решение превысило допустимое время работы '
                    f'в {run_timeout_minutes} минут!'
                ),
            )
            return
        finally:
            shutil.rmtree(evaluation_dir)
            shutil.rmtree(original_dir)

        if completed.returncode != 0:
            error_message = (
                f'Последнее решение завершилось ошибкой (код {completed.returncode}). '
                + 'Привожу stderr:\n\n'
                + completed.stderr
            )
            mlcourse_database.set_error_status(telegram_id)
            bot.send_message(telegram_id, error_message)
        else:
            # FIXME: leaderboard gets updated too often this way but I'm lazy
            update_leaderboard()

            bot.send_message(telegram_id, 'Последнее решение проверено! Нажми /status')
