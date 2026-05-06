from time import sleep

from psycopg2 import OperationalError
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError as AlchemyOpetationalError
from sqlalchemy.orm.query import Query
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

_RETRY_ERRORS = ("server closed the connection unexpectedly",)
_MAX_RETRIES = 10

# Source - https://stackoverflow.com/a/60614707
class RetryingQuery(Query):
    def __iter__(self):
        attempts = 0
        while True:
            attempts += 1
            try:
                return super().__iter__()
            except (OperationalError, AlchemyOpetationalError) as e:
                if not any(msg in str(e) for msg in _RETRY_ERRORS):
                    raise
                if attempts > _MAX_RETRIES:
                    raise
                sleep(2 ** (attempts - 1))


def commit_with_retry(session: Session) -> None:
    attempts = 0
    while True:
        attempts += 1
        try:
            session.commit()
            return
        except (OperationalError, AlchemyOpetationalError) as e:
            if not any(msg in str(e) for msg in _RETRY_ERRORS):
                raise
            if attempts > _MAX_RETRIES:
                raise
            session.rollback()
            sleep(2 ** (attempts - 1))


Base = declarative_base()

def create_db(url: str) -> Session:
    engine = create_engine(url, pool_pre_ping=True, pool_recycle=300)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return SessionLocal(query_cls=RetryingQuery)

def create_local_db() -> Session:
    engine = create_engine("sqlite:///database.db", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return SessionLocal()

