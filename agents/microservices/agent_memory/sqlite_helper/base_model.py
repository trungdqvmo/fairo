import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# TODO: change dbs to weakref
# each microservice will excecute a session
dbs = {}
def safely_load_db(db_path, ):
    if db_path != ':memory:':
        db_path = os.path.abspath(db_path)
    if db_path not in dbs:
        try:
            engine_path = 'sqlite://{}'.format(db_path)
            Session = sessionmaker(bind=engine)
            session = Session()
            #dbs[db_path] = create_engine(engine_path)
        except Exception as e:
            # TODO: change to logging this error
            print(e)
            # TODO: re raise Exception from exception catched
            raise e
    return dbs[db_path]

class BaseModel(object):
    def __init__(self, db_path=':memory:'):
        self._connector = safely_load_db(db_path)

    @property
    def connector(self):
        return self._connector

class session_handler(object):
    def __init__(self):
        pass
