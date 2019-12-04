import sqlite3
from typing import Iterable


def query(conn: sqlite3.Connection, sql: str, params: list) -> Iterable[tuple]:
    cursor = conn.cursor()
    cursor.execute(sql, params)
    yield from cursor
