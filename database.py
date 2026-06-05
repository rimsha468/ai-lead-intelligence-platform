import sqlite3
import json

DB_NAME = "leads.db"


def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project TEXT,
        data TEXT
    )
    """)

    conn.commit()
    conn.close()


def insert_leads(project, leads):
    conn = get_connection()
    c = conn.cursor()

    for lead in leads:
        c.execute(
            "INSERT INTO leads (project, data) VALUES (?, ?)",
            (project, json.dumps(lead))
        )

    conn.commit()
    conn.close()


def get_project_leads(project):
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT data FROM leads WHERE project=?", (project,))
    rows = c.fetchall()

    conn.close()

    return [json.loads(r[0]) for r in rows]