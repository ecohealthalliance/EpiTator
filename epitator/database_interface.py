#!/usr/bin/env python
from .get_database_connection import get_database_connection
import re


class DatabaseInterface(object):
    """
    This interface provides utility methods for the embedded EpiTator database.
    """
    def __init__(self):
        self.db_connection = get_database_connection()

        def dict_factory(cursor, row):
            d = {}
            for idx, col in enumerate(cursor.description):
                d[col[0]] = row[idx]
            return d
        self.db_connection.row_factory = dict_factory

    def lookup_synonym(self, synonym, entity_type):
        cursor = self.db_connection.cursor()
        synonym = re.sub(r"[\s\-\/]+", " ", synonym)
        synonym = re.sub(r"[\"']", "", synonym)
        return cursor.execute('''
        SELECT id, label, synonym, max(weight) AS weight
        FROM synonyms
        JOIN entities ON synonyms.entity_id=entities.id
        WHERE synonym LIKE ? AND entities.type=?
        GROUP BY entity_id
        ORDER BY weight DESC, length(synonym) ASC
        LIMIT 20
        ''', ['%' + synonym + '%', entity_type])

    def get_entity(self, entity_id):
        cursor = self.db_connection.cursor()
        return next(cursor.execute('''
        SELECT *
        FROM entities
        WHERE id = ?
        ''', [entity_id]), None)
