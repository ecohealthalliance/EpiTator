from __future__ import absolute_import
from __future__ import print_function
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
            print("Creating database at:", ANNOTATOR_DB_PATH)
        connection = sqlite3.connect(ANNOTATOR_DB_PATH)
        cur = connection.cursor()
        cur.execute("PRAGMA foreign_keys = ON")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            property TEXT PRIMARY KEY ASC, value TEXT
        )""")
        if not databse_exists:
            # Initialize the database
            cur.execute("""
            CREATE TABLE entities (
                id TEXT PRIMARY KEY, label TEXT, type TEXT, source TEXT
            )""")
            cur.execute("""
            CREATE TABLE synonyms (
                synonym TEXT,
                entity_id TEXT REFERENCES entities(id),
                weight INTEGER
            )""")
            cur.execute('''
            CREATE INDEX synonym_index ON synonyms (synonym);
            ''')
            cur.execute("INSERT INTO metadata VALUES ('dbversion', '0.0.0')")
            connection.commit()
        db_version = next(cur.execute("""
        SELECT value AS version FROM metadata WHERE property = 'dbversion'
        """), None)
        if not db_version or db_version[0] != "0.0.0":
            raise Exception("The database at " + ANNOTATOR_DB_PATH +
                            " has a version that is not compatible by this version of EpiTator.\n"
                            "You will need to rerun the data import scripts.")
        return connection
    else:
        raise Exception("There is no EpiTator database at: " + ANNOTATOR_DB_PATH +
                        "\nRun `python -m epitator.importers.import_all` to create a new database"
                        "\nor set ANNOTATOR_DB_PATH to use a database at a different location.")
