import os
from .sqlite3worker import Sqlite3Worker

# TODO: change dbs to weakref
dbs = {}
def safely_load_db(db_path):
    db_path = os.path.abspath(db_path)
    if db_path not in dbs:
        try:
            dbs[db_path] = Sqlite3Worker(db_path)
        except Exception as e:
            # TODO: change to logging this error
            print(e)
            # TODO: re raise Exception from exception catched
            raise e
    return dbs[db_path]


class BaseModel(object):
    def __init__(self, db_path):
        self._connector = safely_load_db(db_path)

    @property
    def connector(self):
        return self._connector
