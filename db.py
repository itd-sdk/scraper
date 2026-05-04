from time import sleep

from psycopg2 import OperationalError
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError as AlchemyOpetationalError
from sqlalchemy.orm.query import Query
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

# Source - https://stackoverflow.com/a/60614707
class RetryingQuery(Query):
    _max_retry_count = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __iter__(self):
        attempts = 0
        while True:
            attempts += 1
            try:
                return super().__iter__()
            except (OperationalError, AlchemyOpetationalError) as e:
                if "server closed the connection unexpectedly" not in str(e):
                    raise
                if attempts <= self._max_retry_count:
                    sleep_for = 2 ** (attempts - 1)
                    sleep(sleep_for)
                    continue
                else:
                    raise


Base = declarative_base()

def create_db(url: str) -> Session:
    engine = create_engine(url, pool_pre_ping=True, pool_recycle=300)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, query_cls=RetryingQuery)
    Base.metadata.create_all(bind=engine)
    return SessionLocal()

def create_local_db() -> Session:
    engine = create_engine("sqlite:///database.db", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, query_cls=RetryingQuery)
    Base.metadata.create_all(bind=engine)
    return SessionLocal()

