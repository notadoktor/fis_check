from sqlalchemy.orm import Session
from typing import List
from . import models, schemas


def get_racer(db: Session, id: int) -> models.Racer:
    return db.query(models.Racer).filter(models.Racer.id == id).first()


def get_racer_by_name(db: Session, name: str) -> models.Racer:
    return db.query(models.Racer).filter(models.Racer.name == name).first()


def create_racer(db: Session, racer: schemas.RacerBase):
    db_racer = models.Racer(**racer.dict())
    db.add(db_racer)
    db.commit()
    db.refresh(db_racer)
    return db_racer


def get_event(db: Session, id: int) -> models.Event:
    return db.query(models.Event).filter(models.Event.id == id).first()


def create_event(db: Session, event: schemas.EventBase):
    db_event = models.Event(**event.dict())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


def get_races(db: Session, event_id: int) -> List[models.Race]:
    event = get_event(db, event_id)
    return event.races


def get_race(db: Session, id: int) -> models.Race:
    return db.query(models.Race).filter(models.Race.id == id).first()


def create_race(db: Session, race: schemas.RaceBase):
    db_race = models.Race(**race.dict())
    db.add(db_race)
    db.commit()
    db.refresh(db_race)
    return db_race


def get_runs(db: Session, race_id: int) -> List[models.Run]:
    race = get_race(db, race_id)
    return race.runs


def get_run(db: Session, race_id: int, run: int) -> models.Run:
    return (
        db.query(models.Run).filter(models.Run.race_id == race_id and models.Run.run == run).first()
    )


def create_run(db: Session, run: schemas.RunBase):
    db_run = models.Run(**run.dict())
    db.add(db_run)
    db.commit()
    db.refresh(db_run)
    return db_run


def get_results(db: Session, race_id: int) -> List[models.Result]:
    race = get_race(db, race_id)
    return race.results


def get_result_by_bib(db: Session, race_id: int, bib: int) -> models.Result:
    return (
        db.query(models.Result)
        .filter(models.Result.race_id == race_id and models.Result.bib == bib)
        .first()
    )


def get_result_by_racer(db: Session, race_id: int, racer_id: int) -> models.Result:
    return (
        db.query(models.Result)
        .filter(models.Result.race_id == race_id and models.Result.racer_id == racer_id)
        .first()
    )


def create_result(db: Session, result: schemas.ResultBase):
    db_result = models.Result(**result.dict())
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result
