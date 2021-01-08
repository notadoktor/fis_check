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
    breakpoint()
    db_event = crud.get_event(db, eventid)
    if db_event is None:
        event = scrape.Event.load(
            event_id=str(eventid), season_code=str(seasoncode), sector_code=Discipline[sectorcode]
        )
        return event
    else:
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
