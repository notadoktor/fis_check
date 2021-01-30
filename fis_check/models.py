from sqlalchemy import Column, Date, DateTime, Enum, Float, Integer, String, Time, MetaData
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative.api import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.schema import ForeignKey, UniqueConstraint
from sqlalchemy.sql.sqltypes import Boolean

from .enums import Category, Country, SectorCode, EventType, Gender, RunStatus, Status

md: MetaData = MetaData()
Base = declarative_base()
Base.metadata = md


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    place = Column(String, nullable=False)
    country = Column(Enum(Country), nullable=False)
    season_code = Column(Integer, nullable=False)
    sector_code = Column(Enum(SectorCode), nullable=False)
    _status = Column("status", Integer, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    @hybrid_property
    def status(self):
        # breakpoint()
        return self._status

    @status.setter
    def status(self, status: Status):
        self._status = status.value

    races = relationship("Race", back_populates="event")


class Race(Base):
    __tablename__ = "races"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), index=True, nullable=False)
    category = Column(Enum(Category), index=True, nullable=False)
    codex = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    event_type = Column(Enum(EventType), nullable=False)
    gender = Column(Enum(Gender), nullable=False)
    status = Column(Integer)
    comments = Column(String)
    live_url = Column(String)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    runs = relationship("Run", back_populates="race")
    event = relationship("Event", back_populates="races")
    result = relationship("Result", back_populates="race")


class Run(Base):
    __tablename__ = "runs"
    race_id = Column(Integer, ForeignKey("races.id"), primary_key=True)
    run = Column(Integer, nullable=False, primary_key=True)
    cet = Column(Time)
    loc = Column(Time)
    status = Column(Enum(RunStatus))
    info = Column(String)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    race = relationship("Race", back_populates="runs")
    UniqueConstraint(race_id, run)


class Racer(Base):
    __tablename__ = "racers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    country = Column(Enum(Country), nullable=False)
    gender = Column(Enum(Gender), nullable=False)
    fis_code = Column(Integer)
    birth_date = Column(Date)
    skis = Column(String)
    boots = Column(String)
    poles = Column(String)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    results = relationship("Result", back_populates="racer")


class Result(Base):
    __tablename__ = "results"

    race_id = Column(Integer, ForeignKey("races.id"), primary_key=True, index=True)
    racer_id = Column(Integer, ForeignKey("racers.id"), primary_key=True, index=True)
    bib = Column(Integer, nullable=False)
    rank = Column(Integer)
    time = Column(Integer)  # milliseconds
    difference = Column(Integer)  # milliseconds
    fis_points = Column(Float)
    cup_points = Column(Integer)
    dnf = Column(Boolean, default=False)
    dns = Column(Boolean, default=False)

    race = relationship("Race", back_populates="result")
    racer = relationship("Racer", back_populates="results")
