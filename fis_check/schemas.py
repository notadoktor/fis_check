from pydantic import BaseModel, Field, PositiveInt
from typing import Optional, List
import datetime

from .enums import Category, Country, Discipline, EventType, Gender, RunStatus, Status


class EventBase(BaseModel):
    id: int
    place: str
    country: Country
    gender: Gender
    seasoncode: int
    discipline: Discipline


class Event(EventBase):
    # races: List["Race"]

    class Config:
        orm_mode = True


class RaceBase(BaseModel):
    id: int
    event_id: int
    category: Category
    codex: int
    date: datetime.date
    event_type: EventType
    gender: Gender


class Race(RaceBase):
    status: Status
    comments: Optional[str]
    live_url: Optional[str]

    parent: Event
    runs: List["Run"]
    results: List["Result"]

    class Config:
        orm_mode = True


class RunBase(BaseModel):
    race_id: int
    run: PositiveInt


class Run(RunBase):
    status: Optional[RunStatus]
    cet: Optional[datetime.time]
    loc: Optional[datetime.time]
    info: Optional[str]
    parent: Race

    class Config:
        orm_mode = True


class ResultBase(BaseModel):
    race_id: int
    bib: int


class Result(ResultBase):
    racer_id: int
    rank: Optional[int]
    time: Optional[int]
    difference: Optional[int]
    fis_points: Optional[float]
    cup_points: Optional[int]

    parent: Race
    racer: "Racer"

    class Config:
        orm_mode = True


class RacerBase(BaseModel):
    id: int
    name: str
    country: Country
    gender: Gender


class Racer(RacerBase):
    fis_code: Optional[int]
    birth_date: Optional[datetime.date]
    skis: Optional[str]
    boots: Optional[str]
    poles: Optional[str]
    results: List[Result]

    class Config:
        orm_mode = True


###

Event.update_forward_refs()
Race.update_forward_refs()
Run.update_forward_refs()
Result.update_forward_refs()
Racer.update_forward_refs()
