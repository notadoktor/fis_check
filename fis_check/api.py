from copy import deepcopy

from fis_check.enums import SectorCode
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
    return []


@app.get("/event/{event_id}", response_model=schemas.EventLinked)
async def get_cal_event(
    event_id: int, season_code: int = 2021, sector_code: str = "AL", db: Session = Depends(get_db)
):
    db_event = crud.get_event(db, event_id)

    if db_event is None or not db_event.races:
        scraped_event = scrape.Event(
            id=str(event_id), season_code=str(season_code), sector_code=SectorCode[sector_code]
        )

        if db_event is None:
            db_event = crud.create_event(db, schemas.EventBase(**scraped_event.__dict__))

        for r in scraped_event.races:
            rdict = deepcopy(r.__dict__)
            rdict["event_id"] = event_id
            crud.create_race(db, schemas.RaceBase(**rdict))
            if r.runs:
                for run_obj in r.runs:
                    run_dict = deepcopy(run_obj.__dict__)
                    run_dict["race_id"] = rdict["id"]
                    crud.create_run(db, schemas.RunBase(**run_dict))
        db.refresh(db_event)
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
