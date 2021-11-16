import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# TODO: change dbs to weakref
# each microservice will excecute a session
dbs = {}

BaseModel = declarative_base()
meta = MetaData()

class sqlalchemy_session(object):
    def __init__(self, db_path=':memory:'):
        # currently only support sqlite db
        if db_path is not None:
            engine_path = 'sqlite://{}'.format(db_path)
            engine = create_engine(engine_path, echo=False)
            meta.create_all(engine)
            self.session_initor = sessionmaker(bind=engine)
        else:
            self.session_initor = sessionmaker()

    def __call__( self, name):
        if name not in dbs:
            self.session_initor = sessionmaker()
            dbs[name] = self
        return dbs[name]

    def __enter__(self):
        return self

    def __exit__( self, exc_type, exc_val, exc_tb ):
        self.clear()

    def create_all():
        pass
