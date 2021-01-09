from fis_check.enums import Discipline
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from . import crud, models, schemas, scrape
from .db import DB

app = FastAPI()


def get_db():
    db = DB()
    db.ensure_db()
    try:
        yield db.session
    finally:
        db.session.close()


@app.get("/")
async def root():
    return {}


@app.get("/calendar")
async def get_cal():
    # fetch calendar
    pass


@app.get("/event/{eventid}", response_model=schemas.Event)
async def get_cal_event(
    eventid: int, seasoncode: int = 2021, sectorcode: str = "AL", db: Session = Depends(get_db)
):
    db_event = crud.get_event(db, eventid)
    scraped_event = None
    if db_event is None:
        event = scrape.Event.load(
            event_id=str(eventid), season_code=str(seasoncode), sector_code=Discipline[sectorcode]
        )
        db_event = crud.create_event(db, schemas.EventBase(**event.__dict__))

    if not db_event.races:
        if not scraped_event:
            scraped_event = scrape.Event.load(
                str(db_event.id), str(db_event.seasoncode), db_event.discipline, True  # type: ignore
            )
        for r in scraped_event.races:
            rdict = r.__dict__.copy()
            rdict["event_id"] = str(eventid)
            crud.create_race(db, schemas.RaceBase(**rdict))
        db.refresh(db_event)
    # breakpoint()
    return db_event


@app.get("/event/{eventid}/races")
async def get_ev_races(eventid):
    pass


@app.get("/race/{raceid}")
# @app.get("/event/:eventid/:racenum")
async def get_race(raceid):
    pass


@app.get("/race/{raceid}/results")
# @app.get("/event/:eventid/:racenum/results")
async def get_results(raceid):
    pass


@app.get("/racer")
async def list_racers():
    pass


@app.get("/racer/{racerid}")
async def get_racer(racerid):
    pass
