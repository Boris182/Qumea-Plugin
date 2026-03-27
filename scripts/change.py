import sqlite3
from pathlib import Path


DB_PATH = Path("./database/app.db")
TABLE_NAME = "users"
OLD_COLUMN = "user_name"
NEW_COLUMN = "username"


def main():
    if not DB_PATH.exists():
        print(f"Fehler: Datenbank nicht gefunden: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)

    try:
        cursor = conn.cursor()

        # Prüfen, ob Tabelle existiert
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (TABLE_NAME,)
        )
        table = cursor.fetchone()
        if not table:
            print(f"Fehler: Tabelle '{TABLE_NAME}' nicht gefunden.")
            return

        # Spalten der Tabelle lesen
        cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        if NEW_COLUMN in column_names:
            print(f"Die Spalte '{NEW_COLUMN}' existiert bereits. Keine Änderung nötig.")
            return

        if OLD_COLUMN not in column_names:
            print(f"Fehler: Spalte '{OLD_COLUMN}' nicht gefunden.")
            return

        # Spalte umbenennen
        sql = f"ALTER TABLE {TABLE_NAME} RENAME COLUMN {OLD_COLUMN} TO {NEW_COLUMN}"
        cursor.execute(sql)
        conn.commit()

        print(
            f"Erfolg: Spalte '{OLD_COLUMN}' wurde in '{NEW_COLUMN}' umbenannt."
        )

    except sqlite3.OperationalError as e:
        print("SQLite-Fehler beim Umbenennen der Spalte.")
        print(f"Details: {e}")
    except Exception as e:
        print("Unerwarteter Fehler.")
        print(f"Details: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()