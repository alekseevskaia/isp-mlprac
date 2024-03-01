import sqlite3
from datetime import datetime
from typing import Any, List, Optional, Tuple

from zoneinfo import ZoneInfo


def transaction(method):
    def wrapped(obj, *args, **kwargs):
        with obj.connection:
            obj.cursor = obj.connection.cursor()
            return_value = method(obj, *args, **kwargs)
            obj.cursor.close()
        return return_value

    return wrapped


class MlcourseDatabase:
    def __init__(self, db_file_path: str) -> None:
        self.connection: sqlite3.Connection = sqlite3.connect(db_file_path, check_same_thread=False)
        self.cursor: Optional[sqlite3.Cursor] = None

        self.create_tables()

    @transaction
    def create_tables(self) -> None:
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS students(
            telegram_id INTEGER PRIMARY KEY,
            full_name TEXT,
            student_id INTEGER
        );
        """
        )
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS solutions(
            solution_id INTEGER PRIMARY KEY,
            telegram_id INTEGER,
            time_sent DATETIME,
            status TEXT,
            badnets_clean REAL,
            badnets_poisoned REAL,
            lira_clean REAL,
            lira_poisoned REAL,
            FOREIGN KEY(telegram_id) REFERENCES students(telegram_id)
        );
        """
        )

    @transaction
    def set_student_full_name(self, telegram_id: int, full_name: str) -> None:
        self.cursor.execute(
            """INSERT INTO students(telegram_id, full_name) VALUES(?,?)
            ON CONFLICT(telegram_id) DO UPDATE SET full_name=excluded.full_name;
        """,
            (telegram_id, full_name),
        )

    @transaction
    def set_student_id(self, telegram_id: int, student_id: int) -> None:
        self.cursor.execute(
            """INSERT INTO students(telegram_id, student_id) VALUES(?,?)
            ON CONFLICT(telegram_id) DO UPDATE SET student_id=excluded.student_id;
        """,
            (telegram_id, student_id),
        )

    @transaction
    def get_student_info(self, telegram_id: int) -> Optional[Tuple[str, Optional[int]]]:
        row = self.cursor.execute(
            'SELECT full_name, student_id FROM students WHERE telegram_id=?;', (telegram_id,)
        ).fetchone()
        return row

    @transaction
    def submit_solution(self, telegram_id: int) -> None:
        now = datetime.now(tz=ZoneInfo('Europe/Moscow'))
        self.cursor.execute(
            'DELETE FROM solutions WHERE telegram_id=? AND status=?;', (telegram_id, 'new')
        )
        self.cursor.execute(
            'INSERT INTO solutions(telegram_id, time_sent, status) VALUES (?,?,?);',
            (telegram_id, now, 'new'),
        )

    @transaction
    def pull_oldest_new_solution(self) -> Optional[Tuple[int, datetime]]:
        row = self.cursor.execute(
            """SELECT solution_id, telegram_id, time_sent FROM solutions
            WHERE status=? ORDER BY time_sent;""",
            ('new',),
        ).fetchone()
        if not row:
            return None

        solution_id, telegram_id, time_sent = row
        self.cursor.execute(
            'UPDATE solutions SET status=? WHERE solution_id=?;', ('in_progress', solution_id)
        )
        return telegram_id, time_sent

    @transaction
    def set_badnets_scores(self, telegram_id: int, clean: float, poisoned: float) -> None:
        self.cursor.execute(
            """UPDATE solutions SET badnets_clean=?, badnets_poisoned=?, status=?
            WHERE telegram_id=? AND status=?;""",
            (clean, poisoned, 'done', telegram_id, 'in_progress'),
        )

    @transaction
    def set_lira_scores(self, telegram_id: int, clean: float, poisoned: float) -> None:
        self.cursor.execute(
            """UPDATE solutions SET lira_clean=?, lira_poisoned=?, status=?
            WHERE telegram_id=? AND status=?;""",
            (clean, poisoned, 'done', telegram_id, 'in_progress'),
        )

    @transaction
    def get_top_solution(
        self, telegram_id: int, task: str = 'badnets', best_or_latest: str = 'best'
    ) -> Optional[Tuple[Any, ...]]:
        order_by = f'{task}_poisoned' if best_or_latest == 'best' else 'time_sent'
        return self.cursor.execute(
            f"""SELECT time_sent, {task}_clean, {task}_poisoned FROM solutions
            WHERE telegram_id=? AND {task}_poisoned IS NOT NULL
            ORDER BY {order_by} DESC LIMIT 1;""",
            (telegram_id,),
        ).fetchone()

    @transaction
    def get_leaderboard(self, task: str = 'badnets') -> List[Tuple[Any, ...]]:
        return self.cursor.execute(
            f"""WITH task_solutions AS
            (
                SELECT solution_id, telegram_id, time_sent, {task}_clean, {task}_poisoned
                FROM solutions WHERE {task}_poisoned IS NOT NULL
            ),
            solution_ranks AS
            (
                SELECT solution_id,
                ROW_NUMBER() OVER (PARTITION BY telegram_id ORDER BY {task}_poisoned DESC) AS rn
                FROM task_solutions
            ),
            solution_counts AS
            (
                SELECT telegram_id, COUNT(*) AS solution_count FROM task_solutions
                GROUP BY telegram_id
            )
            SELECT full_name, student_id, {task}_poisoned, {task}_clean, time_sent, solution_count
            FROM students
                JOIN task_solutions ON students.telegram_id=task_solutions.telegram_id
                JOIN solution_ranks ON task_solutions.solution_id=solution_ranks.solution_id
                JOIN solution_counts ON students.telegram_id=solution_counts.telegram_id
            WHERE rn=1 ORDER BY {task}_poisoned DESC;"""
        ).fetchall()

    @transaction
    def set_error_status(self, telegram_id: int) -> None:
        self.cursor.execute(
            'UPDATE solutions SET status=? WHERE telegram_id=? AND status=?;',
            ('error', telegram_id, 'in_progress'),
        )

    @transaction
    def get_unchecked_solution_status(self, telegram_id: int) -> Optional[str]:
        new_or_in_progress = self.cursor.execute(
            'SELECT status FROM solutions WHERE telegram_id=? AND (status=? OR status=?)',
            (telegram_id, 'new', 'in_progress'),
        ).fetchone()

        return None if new_or_in_progress is None else new_or_in_progress[0]

    def __del__(self) -> None:
        self.connection.close()


mlcourse_database = MlcourseDatabase(db_file_path='/solutions/solutions.db')
