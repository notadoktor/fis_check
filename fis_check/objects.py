import datetime
from typing import List, Optional
from .enums import Category, Country, Discipline, Event, Gender, Status


class BaseObject:
    id: str

    def __init__(self, id: str, **kwargs) -> None:
        self.id = id
        for key in kwargs:
            if hasattr(self, key):
                setattr(self, key, kwargs[key])
            else:
                raise KeyError(f"Invalid attribiute: {key}")


class RaceEvent(BaseObject):
    status: List[str] = []
    dates: List[datetime.date]
    place: str
    country: Country
    discipline: Discipline
    categories: List[Category]
    gender: Gender

    def load(self) -> "RaceEvent":
        raise NotImplemented


class Race(BaseObject):
    status: Status
    date: datetime.date
    codex: str
    live_url: Optional[str]
    events: List[Event]
    categories: List[Category]
    gender: Gender

    def load(self) -> "Race":
        raise NotImplemented


class Racer(BaseObject):
    name: str
    fis_code: str
    birth_year: int
    gender: Gender
    nation: Country

    def load(self) -> "Racer":
        raise NotImplemented

    @classmethod
    def fetch(cls, id: str) -> "Racer":
        racer = cls(id)
        return racer.load()


class RaceResult:
    rank: int
    bib: int
    fis_code: str
    name: str
    birth_year: int
    nation: Country
    time: str
    difference: str
    fis_points: Optional[float]
    cup_points: Optional[int]
    racer: Racer

    def __init__(
        self,
        rank: int,
        bib: int,
        time: str,
        difference: str,
        name: str = None,
        fis_points: float = None,
        cup_points: int = None,
        racer_id: str = None,
    ) -> None:
        self.rank = rank
        self.bib = bib
        self.time = time
        self.difference = difference
        if fis_points is not None:
            self.fis_points = fis_points
        if cup_points is not None:
            self.cup_points = cup_points
        if name:
            self.name = name
        elif racer_id:
            self.racer = Racer(racer_id)
            self.racer.load()
        else:
            raise ValueError(f"You must give either a racer name or id")
