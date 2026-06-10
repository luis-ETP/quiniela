import os
import psycopg
from psycopg.rows import dict_row

def get_conn():
    return psycopg.connect(os.environ.get("DATABASE_URL"), row_factory=dict_row)

def query(sql, params=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            try:
                return cur.fetchall()
            except:
                return []

def execute(sql, params=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
        conn.commit()
