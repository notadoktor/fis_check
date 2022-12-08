import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, PositiveInt

from .enums import Category, Country, EventType, Gender, RunStatus, SectorCode, Status


# TODO: fix meta status in model / schema
class EventBase(BaseModel):
    id: int
    status: Status
    place: str
    country: Country
    season_code: int
    sector_code: SectorCode


class Event(EventBase):
    updated_at: datetime.date

    class Config:
        orm_mode = True


class EventLinked(Event):
    races: List["Race"]


class RaceBase(BaseModel):
    id: int
    event_id: int
    category: Category
    codex: int
    date: datetime.date
    event_type: EventType
    gender: Gender
    status: Status


class Race(RaceBase):
    comments: Optional[str]
    live_url: Optional[str]

    class Config:
        orm_mode = True


class RaceLinked(Race):
    runs: List["Run"]
    results: List["Result"]


class RunBase(BaseModel):
    race_id: int
    run: PositiveInt
    status: Optional[RunStatus]
    cet: Optional[datetime.time]
    loc: Optional[datetime.time]
    info: Optional[str]


class Run(RunBase):
    updated_at: datetime.datetime

    class Config:
        orm_mode = True


class RunLinked(Run):
    race: Race


class ResultBase(BaseModel):
    race_id: int
    bib: int


class Result(ResultBase):
    racer_id: int
    rank: Optional[str]
    time: Optional[str]
    difference: Optional[str]
    fis_points: Optional[float]
    cup_points: Optional[int]

    class Config:
        orm_mode = True


class ResultLinked(Result):
    race: Race
    racer: "Racer"


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

    class Config:
        orm_mode = True


###

Event.update_forward_refs()
EventLinked.update_forward_refs()
Race.update_forward_refs()
RaceLinked.update_forward_refs()
Run.update_forward_refs()
RunLinked.update_forward_refs()
Result.update_forward_refs()
ResultLinked.update_forward_refs()
Racer.update_forward_refs()
