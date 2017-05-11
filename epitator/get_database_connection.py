import os
import sqlite3
if os.environ.get('ANNOTATOR_DB_PATH'):
    ANNOTATOR_DB_PATH = os.environ.get('ANNOTATOR_DB_PATH')
else:
    ANNOTATOR_DB_PATH = os.path.expanduser("~") + '/.epitator.sqlitedb'


def get_database_connection(create_database=False):
    databse_exists = os.path.exists(ANNOTATOR_DB_PATH)
    if databse_exists or create_database:
        if not databse_exists:
            print "Creating database at:", ANNOTATOR_DB_PATH
        return sqlite3.connect(ANNOTATOR_DB_PATH)
    else:
        raise Exception("There is no EpiTator database at: " + ANNOTATOR_DB_PATH +
                        "\nRun `python -m epitator.sqlite_import_geonames` to create a new database"
                        "\nor set ANNOTATOR_DB_PATH to use a database at a different location.")
