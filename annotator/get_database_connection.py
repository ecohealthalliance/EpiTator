import os
import sqlite3
ANNIE_DB_PATH = os.environ.get('ANNIE_DB_PATH') or os.path.expanduser("~") + '/.annie.sqlitedb'
def get_database_connection():
    if not os.path.exists(ANNIE_DB_PATH):
        raise Exception("There is no annie database at: " + ANNIE_DB_PATH +
            "\nRun `python -m annotator.sqlite_import_geonames` to create a new database"
            "\nor set ANNIE_DB_PATH to use a database at a different location.")
    return sqlite3.connect(ANNIE_DB_PATH)
