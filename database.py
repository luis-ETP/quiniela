import os
import psycopg2
import psycopg2.extras

def get_db():
    conn = psycopg2.connect(
        os.environ.get("DATABASE_URL"),
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    conn.autocommit = True
    return conn

def query(sql, params=None):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(sql, params or ())
    try:
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    except:
        return []
    finally:
        conn.close()

def execute(sql, params=None):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(sql, params or ())
    conn.close()
