from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import scoped_session, sessionmaker

from .models import Base

# use PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE env vars for connection
default_db_url = "postgresql://"


class DB(object):
    engine: Engine
    metadata: MetaData = Base.metadata
    session: scoped_session

    def __init__(self, db_url: str = default_db_url, engine: Engine = None) -> None:
        if engine:
            self.engine = engine
        elif db_url:
            self.engine = create_engine(db_url)
        self._init_session()

    def _init_session(self) -> None:
        self.session_maker = sessionmaker(bind=self.engine)
        self.session = self.session_maker()

    def connect(self, *args, **kwargs) -> None:
        if getattr(self, "session", None) and self.session.is_active:
            # use existing session
            return

        self._init_session()

    def create_db(self) -> None:
        Base.metadata.create_all(self.engine)

    def disconnect(self) -> None:
        if hasattr(self, "session"):
            self.session.close()

    def ensure_db(self) -> None:
        assert (
            getattr(self, "session", None) is not None and getattr(self, "engine", None) is not None
        )
        if not all([self.engine.has_table(t.name) for t in self.metadata.sorted_tables]):
            self.create_db()
