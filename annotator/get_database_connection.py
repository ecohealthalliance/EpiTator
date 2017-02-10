import os
import sqlite3
if os.environ.get('ANNOTATOR_DB_PATH'):
    ANNOTATOR_DB_PATH = os.environ.get('ANNOTATOR_DB_PATH')
else:
    ANNOTATOR_DB_PATH = os.path.expanduser("~") + '/.annie.sqlitedb'
def get_database_connection():
    if not os.path.exists(ANNOTATOR_DB_PATH):
        raise Exception("There is no annie database at: " + ANNOTATOR_DB_PATH +
            "\nRun `python -m annotator.sqlite_import_geonames` to create a new database"
            "\nor set ANNOTATOR_DB_PATH to use a database at a different location.")
    return sqlite3.connect(ANNOTATOR_DB_PATH)
