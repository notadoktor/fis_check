from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from . import crud, models, schemas, scrape
from .db import SessionLocal, engine

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
async def root():
    pass


@app.get("/calendar")
async def get_cal():
    # fetch calendar
    pass


@app.get("/event/{eventid}", response_model=schemas.Event)
async def get_cal_event(eventid: int, db: Session = Depends(get_db)):
    db_event = crud.get_event(db, eventid)
    if db_event is None:
        event = scrape.Event(id=str(eventid))


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