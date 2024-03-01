import base64
from pathlib import Path

import requests
from tabulate import tabulate

from mlcourse_prac.config import CONFIG
from mlcourse_prac.db import mlcourse_database


def wordpress_request(leaderboard_html: str) -> None:
    username = CONFIG['wordpress']['username']
    password = CONFIG['wordpress']['password']
    page_id = CONFIG['wordpress']['page_id']

    url = 'https://mlcourse.at.ispras.ru/wp-json/wp/v2/pages/' + page_id
    token = base64.b64encode(f'{username}:{password}'.encode()).decode()
    header = {'Authorization': 'Basic ' + token}
    payload = {'content': leaderboard_html}

    requests.post(url, headers=header, json=payload)


def update_leaderboard() -> None:
    # FIXME: only 'badnets' leaderboard is generated for now
    leaderboard = mlcourse_database.get_leaderboard()

    headers = [
        'Место',
        'ФИО',
        'Студбилет',
        'С атакой',
        'Без атаки',
        'Дата лучшего решения',
        'Кол-во решений',
    ]
    tabular_data = []
    for idx, row in enumerate(leaderboard):
        rank = idx + 1
        full_name, student_id, poisoned, clean, time_sent, count = row
        tabular_data.append(
            [
                rank,
                full_name,
                student_id,
                f'{poisoned:.4f}',
                f'{clean:.4f}',
                time_sent.strftime('%d.%m %H:%M'),
                count,
            ]
        )
    table = tabulate(tabular_data, headers=headers, tablefmt='html', stralign='center')

    paragraph = (
        '<!-- wp:paragraph --><p>Выводятся результаты лучшего решения!</p><!-- /wp:paragraph -->'
    )
    block_start = '<!-- wp:code --><pre class="wp-block-code"><code>'
    style_path = Path(__file__).resolve().parent / 'style.css'
    with style_path.open() as f:
        style = '<style>' + f.read() + '</style>'
    block_end = '</code></pre><!-- /wp:code -->'
    html = paragraph + block_start + style + table + block_end

    wordpress_request(html)
