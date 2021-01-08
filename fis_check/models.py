from sqlalchemy import Column, Date, Enum, Float, Integer, String, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import ForeignKey

from .db import Base
from .enums import Category, Country, Discipline, EventType, Gender, RunStatus, Status


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    place = Column(String, nullable=False)
    country = Column(Enum(Country), nullable=False)
    gender = Column(Enum(Gender), nullable=False)
    seasoncode = Column(Integer, nullable=False)
    discipline = Column(Enum(Discipline), nullable=False)
    status = Column(Enum(Status))

    races = relationship("Race", back_populates="event")


class Race(Base):
    __tablename__ = "races"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), index=True, nullable=False)
    category = Column(Enum(Category), index=True, nullable=False)
    codex = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    event = Column("event_type", Enum(EventType), nullable=False)
    gender = Column(Enum(Gender), nullable=False)
    status = Column(Enum(Status))
    comments = Column(String)
    live_url = Column(String)

    runs = relationship("Run", back_populates="race")
    event = relationship("Event", back_populates="races")
    result = relationship("Result", back_populates="race")


class Run(Base):
    __tablename__ = "runs"
    race_id = Column(Integer, ForeignKey("races.id"), primary_key=True)
    run = Column(Integer, unique=True, nullable=False, primary_key=True)
    cet = Column(Time)
    loc = Column(Time)
    status = Column(Enum(RunStatus))
    info = Column(String)

    race = relationship("Race", back_populates="runs")


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

    results = relationship("Result", back_populates="racer")


class Result(Base):
    __tablename__ = "results"

    race_id = Column(Integer, ForeignKey("races.id"), primary_key=True)
    racer_id = Column(Integer, ForeignKey("racers.id"), primary_key=True)
    bib = Column(Integer, nullable=False)
    rank = Column(Integer)
    time = Column(Integer)  # milliseconds
    difference = Column(Integer)  # milliseconds
    fis_points = Column(Float)
    cup_points = Column(Integer)

    race = relationship("Race", back_populates="result")
    racer = relationship("Racer", back_populates="results")
