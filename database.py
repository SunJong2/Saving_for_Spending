import os
import psycopg
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    raise RuntimeError("DATABASE_URL이 설정되지 않았습니다. .env 파일을 확인하세요")


@contextmanager
def get_db():
    """DB 연결을 열고, 블록이 끝나면 반드시 닫는다 (예외가 나도 닫힘)"""
    conn = psycopg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nickname TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                target_amount INTEGER NOT NULL,
                current_amount INTEGER NOT NULL DEFAULT 0,
                deadline TEXT NOT NULL,
                is_completed BOOLEAN NOT NULL DEFAULT FALSE,
                image_url TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS savings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                goal_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                amount INTEGER NOT NULL,
                memo TEXT,
                image_url TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (goal_id) REFERENCES goals(id)
            )
        """)

        conn.commit()