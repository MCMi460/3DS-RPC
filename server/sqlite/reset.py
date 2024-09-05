import sqlite3


def execute_sql_file(db_file, sql_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    with open(sql_file, 'r') as file:
        sql_script = file.read()

    try:
        cursor.executescript(sql_script)
        print("SQL commands executed successfully.")
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        conn.commit()
        conn.close()


db_file = 'fcLibrary.db'
sql_file = 'CREATE.sql'

execute_sql_file(db_file, sql_file)
