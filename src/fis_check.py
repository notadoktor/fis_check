#!/usr/bin/env python3

import datetime
import logging
import re
from collections import defaultdict
from enum import Flag
from typing import Any, Dict, List, Optional, Union
from urllib.parse import parse_qsl, urlencode, urlparse

import click
import requests
from bs4 import BeautifulSoup

from enums import Category, Country, Discipline, Event, Gender, Status
from util import Cache, RaceFilter, merge_status

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


# classes


class Calendar:
    url: str = "https://www.fis-ski.com/DB/alpine-skiing/calendar-results.html"

    def __init__(
        self,
        seasoncode: str = "2021",
        disciplinecode: Discipline = Discipline.AL,
        categorycode: Category = Category.WC,
    ) -> None:
        self.seasoncode = seasoncode
        self.disciplinecode = disciplinecode
        self.categorycode = categorycode
        self.cache = Cache("calendar")
        self.form_cache = Cache(
            "calendar_form", ctype="json", expire_in=datetime.timedelta(days=90)
        )
        self.event_cache = Cache("calendar_events")
        self._events: List["CalendarEvent"] = []
        self._options: Dict[str, Any] = {}

    @property
    def options(self):
        if not self._options:
            self._load_options()
        return self._options

    def _build_query(self, **opts) -> Dict[str, str]:
        cal_qs = {
            "sector_code": self.disciplinecode,
            "seasoncode": self.seasoncode,
            "categorycode": self.categorycode,
        }
        for q in self.options:
            if q in opts and opts[q] is not None:
                opt_val = opts[q]
                q_reqs = self.options[q]
                if q_reqs["type"] == "input":
                    if q_reqs["pattern"] and not re.compile(q_reqs["pattern"].search(opt_val)):
                        continue
                    elif q_reqs["maxlength"] and len(opt_val) > q_reqs["maxlength"]:
                        continue
                    cal_qs[q] = str(opt_val)
                elif q_reqs["type"] == "select":
                    if isinstance(opt_val, list) and not q_reqs["multiple"]:
                        raise ValueError(f"Cannot provide mutiple values for {q}")
                    elif not isinstance(opt_val, list):
                        opt_val = list(opt_val)

                    for sub_val in opt_val:
                        if str(sub_val) not in q_reqs["opts"].values():
                            raise ValueError(f"Invalid {q} option: {sub_val}")
                    cal_qs[q] = ",".join([str(sv) for sv in opt_val])
                else:
                    raise KeyError(f"Got unexpected query option type: {q_reqs['type']}")
            elif "default" in self.options[q] and q not in cal_qs:
                cal_qs[q] = self.options[q]["default"]

        return cal_qs

    def _load_options(self, skip_cache: bool = False):
        if not skip_cache and not self.form_cache.expired:
            self._options = self.form_cache.load()

        resp = requests.get(self.url)
        if not resp.ok:
            logging.error(f"{resp.status_code}: {resp.text}")
            exit(1)
        bs = BeautifulSoup(resp.text, "lxml")

        self._options = defaultdict(dict)
        form = bs.find("form", attrs={"id": "calendar-filter"})
        if form is None:
            logging.error("Could not find the calendar form")
            exit(1)

        # grab inputs with defaults/restrictions
        for i in form.find_all("input"):
            self._options[i["id"]] = {
                "type": "input",
                "default": i["value"],
                "pattern": i.get("pattern", None),
                "maxlength": i.get("maxlength", None),
            }

        # grab selects with defaults
        for sel in form.find_all("select"):
            sel_options = self._options[sel["id"]]
            sel_options["type"] = "select"
            sel_options["opts"] = {}
            if "multiple" in sel.attrs:
                sel_options["multiple"] = True
            for opt in sel.find_all("option"):
                if "disabled" in opt.attrs:
                    continue
                if "selected" in opt.attrs:
                    sel_options["default"] = opt["value"]
                sel_options["opts"][opt.string] = opt["value"]

        self.form_cache.write(self._options)

    def parse_date(self, date_str: str) -> List[datetime.date]:
        days, month, year = date_str.split()
        if "-" in days:
            min_day, max_day = [int(d) for d in days.split("-")]
        else:
            min_day = max_day = int(days)
        date_list = []
        for dom in range(min_day, max_day + 1):
            date_list.append(datetime.datetime.strptime(f"{dom} {month} {year}", "%d %b %Y").date())
        return date_list

    def scan(self, skip_cache: bool = False, **kwargs) -> List["CalendarEvent"]:
        cal_qs = self._build_query(**kwargs)
        self.event_cache.params = cal_qs.copy()
        if not skip_cache and not self.event_cache.expired:
            self._events = self.event_cache.load()
            logging.debug(f"Using cached event data")
            return self._events

        self._load_options(skip_cache)

        cal_page = BeautifulSoup(self.text(cal_qs), "lxml")
        cal = cal_page.find("div", attrs={"id": "calendarloadcontainer", "class": "section__body"})
        cal_header = [
            d.string
            for d in cal.find("div", attrs={"class": "table__head"}).div.div.div.children
            if visible_div(d)
        ]

        cal_body = cal.find("div", attrs={"id": "calendardata", "class": "tbody"})
        events: List[CalendarEvent] = []
        for cal_row in cal_body.children:
            if cal_row.name != "div":
                continue
            row_data = cal_row.find("div", attrs={"class": "g-row"})
            event_raw = dict(zip(cal_header, [c for c in row_data.children if visible_a(c)]))
            event_data = {"id": cal_row["id"]}
            event_data["status"] = merge_status(
                [s["title"] for s in event_raw["Status"].find_all("span")]
            )

            event_data["dates"] = self.parse_date(event_raw["Date"].string)
            if event_data["dates"][0] > datetime.date.today():
                break
            event_data["place"] = str(event_raw["Place"].div.string)
            event_data["country"] = Country[
                event_raw["Country"].find("span", attrs={"class": "country__name-short"}).string
            ]

            event_data["discipline"] = Discipline[event_raw["Disc."].string]
            cats, evs = [
                d.div.string for d in event_raw["Category & Event"].div.contents if d.name == "div"
            ]
            if " • " in cats:
                event_data["categories"] = [Category[k] for k in cats.split(" • ")]
            else:
                event_data["categories"] = [Category[cats]]

            if " • " in evs:
                event_data["events"] = [Event[re.sub(r"^\dx", "", k)] for k in evs.split(" • ")]
            else:
                event_data["events"] = [Event[re.sub(r"^\dx", "", evs)]]
            event_data["gender"] = Gender[event_raw["Gender"].div.div.div.string]
            events.append(CalendarEvent(**event_data))
        self._events = events
        self.event_cache.write(self._events)
        return self._events

    def text(self, qs: Dict[str, str], skip_cache: bool = False) -> str:
        self.cache.params = qs.copy()
        if self.cache.expired or skip_cache:
            resp = requests.get(self.url, params=qs)
            if not resp.ok:
                logging.error(f"{resp.status_code}: {resp.text}")
                breakpoint()
                exit(1)
            self.cache.write(resp.text)
            return resp.text
        else:
            logging.debug(f"Loading cached calendar page")
            return self.cache.load()


class CalendarEvent:
    url: str = "https://www.fis-ski.com/DB/general/event-details.html"

    def __init__(
        self,
        id: str,
        dates: List[datetime.date],
        place: str,
        country: Country,
        categories: List[Category],
        events: List[Event],
        gender: Gender,
        seasoncode: str = "2021",
        discipline: Discipline = Discipline.AL,
        status=Status(0),
    ) -> None:
        self.id = id
        self.dates = dates
        self.place = place
        self.country = country
        self.categories = categories
        self.events = events
        self.gender = gender
        self.seasoncode = seasoncode
        self.discipline = discipline
        self.status = status
        self._races: List["Race"] = list()

    def __repr__(self) -> str:
        return f"<CalendarEvent id={self.id} place=\"{self.place}\" gender={self.gender.name} events={','.join([e.name for e in self.events])} start={self.dates[0]}>"

    def races(self, skip_cache=False, f: RaceFilter = None) -> List["Race"]:
        if not self._races or skip_cache:
            self.load_races(skip_cache)

        if f:
            return [r for r in self._races if r.filtered(f)]
        return self._races

    def load_races(self, skip_cache: bool = False) -> List["Race"]:
        if self._races and not skip_cache:
            logging.debug(f"using cached race data for {self}")
            return self._races

        event_qs = {
            "sectorcode": self.discipline.name,
            "seasoncode": self.seasoncode,
            "eventid": self.id,
        }
        event_resp = requests.get(self.url, params=event_qs)
        if not event_resp.ok:
            logging.error(f"{event_resp.status_code}: {event_resp.text}")
            breakpoint()
            exit(1)
        # breakpoint()

        event_page = BeautifulSoup(event_resp.text, "lxml")
        race_table = event_page.find("div", attrs={"class": "table_pb"})
        header_obj, subheader_obj = [
            d.div.div for d in race_table.find_all("div", attrs={"class": "thead"})
        ]
        header = [
            d.string if d.string else d.div.string for d in header_obj.children if visible_div(d)
        ]
        runs_header = [
            d.string.strip()
            for d in subheader_obj.find("div", attrs={"class": "g-row"}).children
            if d.name == "div"
        ]

        body_obj = race_table.find("div", attrs={"class": "table__body"})
        for day_obj in [d.div.div.div for d in body_obj.children if d.name == "div"]:
            race_raw = dict(
                zip(header, [tag for tag in day_obj.children if visible_a(tag) or visible_div(tag)])
            )

            race_args: Dict[str, Any] = {}
            race_args["id"] = dict(parse_qsl(urlparse(day_obj.a["href"]).query))["raceid"]
            race_args["status"] = merge_status(
                [s["title"] for s in race_raw["Status"].find_all("span")]
            )
            race_args["date"] = (
                datetime.datetime.strptime(race_raw["Date"].div.div.div.string, "%d %b")
                .replace(year=int(event_qs["seasoncode"]))
                .date()
            )
            if race_args["date"].month > 7:
                race_args["date"] = race_args["date"].replace(year=race_args["date"].year - 1)

            # if <a>, no live result link, just a bare codex string
            if race_raw["Codex"].name == "a":
                race_args["codex"] = str(race_raw["Codex"].string)
            else:
                # if <div>, save link result URL and extract codex from deeper divs
                race_args["live_url"] = race_raw["Codex"].a["href"]
                race_args["codex"] = str(race_raw["Codex"].a.div.div.div.string)
            race_args["event"] = Event(list(race_raw["Event"].stripped_strings)[0])
            race_args["category"] = Category[race_raw["Category"].string]
            race_args["gender"] = Gender[list(race_raw["Gender"].stripped_strings)[0]]
            run_info = race_raw["Runs"].find("div", attrs={"class": "g-row"})
            if run_info:
                race_args["runs"] = dict(
                    zip(
                        runs_header,
                        [
                            d.string.strip() if d.string else ""
                            for d in run_info.children
                            if d.name == "div"
                        ],
                    )
                )
            else:
                race_args["runs"] = {}
            race_args["comments"] = race_raw["Comments"].string if race_raw.get("Comments") else ""

            # breakpoint()
            self._races.append(Race(**race_args))

        return self._races


class Race:
    url: str = "https://www.fis-ski.com/DB/general/results.html"

    def __init__(
        self,
        id: str,
        category: Category,
        codex: str,
        date: datetime.date,
        event: Event,
        gender: Gender,
        status: Status,
        comments: str = None,
        live_url: str = None,
        runs: Dict[str, Any] = None,
    ) -> None:
        self.id = id
        self.category = category
        self.codex = codex
        self.date = date
        self.event = event
        self.gender = gender
        self.status = status
        self.comments = comments
        self.live_url = live_url
        self.runs = runs
        self._results: List["RaceResult"] = []

    def __repr__(self) -> str:
        return f"<Race id={self.id} date={self.date} event={self.event} gender={self.gender}>"

    def filtered(self, f: RaceFilter) -> bool:
        for k, val in f._asdict().items():
            if val is not None:
                r_val = getattr(self, k, None)
                if isinstance(val, Flag):
                    if val not in r_val:
                        return False
                elif isinstance(val, bool):
                    if bool(r_val) != val:
                        return False
                elif type(val) == type(r_val):
                    if val != r_val:
                        return False
        return True

    def results(self, top: int = 10, skip_cache: bool = False) -> List["RaceResult"]:
        if Status.Cancelled in self.status:
            logging.error(f"No results, race was cancelled")
            return []

        self.load_results(skip_cache)
        if len(self._results) >= top:
            return self._results[:top]
        else:
            logging.warning(
                f"Could not return top {top} results, returning all {len(self._results)}"
            )
            return self._results

    def load_results(self, skip_cache: bool = False):
        if not self._results or skip_cache:
            qs = {"raceid": self.id, "sectorcode": "AL"}
            resp = requests.get(Race.url, params=qs)
            if not resp.ok:
                logging.error(f"{resp.status_code}: {resp.text}")
                breakpoint()
                exit(1)

            result_table = (
                BeautifulSoup(resp.text, "lxml").find("div", id="events-info-results").div
            )
            result_rows = [a for a in result_table.children if a.name == "a"]
            header = [
                "rank",
                "bib",
                "FIS code",
                "name",
                "birth year",
                "nation",
                "time",
                "difference",
                "FIS points",
                "cup points",
            ]
            all_results = []
            for row in result_rows:
                row_cols = row.div.div
                row = dict(
                    zip(header, [d.stripped_strings for d in row_cols.children if d.name == "div"])
                )
                rr_attrs: Dict[str, Any] = dict()
                for k, v in row.items():
                    k = k.lower().replace(" ", "_")
                    vlist = list(v)
                    if k in ["rank", "bib", "cup points"]:
                        rr_attrs[k] = int(vlist[0]) if len(vlist) else 0
                    elif k == "difference":
                        rr_attrs[k] = "" if rr_attrs["rank"] == 1 else vlist[0]
                    elif k == "FIS points":
                        rr_attrs[k] = float(vlist[0]) if len(vlist) else float(0)
                    else:
                        rr_attrs[k] = vlist[0] if len(vlist) else ""
                rr = RaceResult(**rr_attrs)
                all_results.append(rr)

            self._results = all_results

    def summarize(self, top: int = 5, show_top: bool = False) -> None:
        max_bin = 0
        for r in self.results(top=top):
            if show_top:
                print(str(r))
            if r.bin > max_bin:
                max_bin = r.bin
        print(f"Max bin: {max_bin}")


class Racer:
    birth_year: int
    fis_code: str
    gender: Gender
    name: str
    nation: Country

    def __init__(self, id: str, load: bool = False, **kwargs) -> None:
        self.id = id
        if load:
            self.load()

    def load(self) -> "Racer":
        raise NotImplemented

    @classmethod
    def fetch(cls, id: str) -> "Racer":
        return cls(id, load=True)


class RaceResult:
    def __init__(
        self,
        rank: int,
        bib: int,
        time: str,
        difference: str,
        name: str,
        nation: Country,
        fis_points: float = None,
        cup_points: int = None,
        racer_id: str = None,
        birth_year: int = None,
        fis_code: str = None,
        racer: Racer = None,
    ) -> None:
        self.rank = rank
        self.bib = bib
        self.time = time
        self.difference = difference
        self.name = name
        self.nation = nation
        if fis_points is not None:
            self.fis_points = fis_points
        if cup_points is not None:
            self.cup_points = cup_points
        if racer_id:
            self.racer = Racer(racer_id)
            self.racer.load()

    def __str__(self) -> str:
        return f"{self.rank}\t{self.bib: 2}\t{self.name: <30}\t{self.nation}\t{self.time: <10}\t{self.difference: <10}"

    @property
    def bin(self) -> int:
        return self.bib // 10 + (1 if self.bib % 10 else 0)


# funcs
hidden_class = r"hidden-[^-\s]+?-up"


def visible_a(tag) -> bool:
    return (
        tag
        and tag.name == "a"
        and (
            not tag.has_attr("class") or not any([re.match(hidden_class, c) for c in tag["class"]])
        )
    )


def visible_div(tag) -> bool:
    return (
        tag
        and tag.name == "div"
        and (
            not tag.has_attr("class") or not any([re.match(hidden_class, c) for c in tag["class"]])
        )
    )


def str2event(ctx, param, val_list: str) -> List[Event]:
    ev_list = []
    for val in val_list:
        if not isinstance(val, Event):
            try:
                val = Event(val.upper())
            except KeyError:
                raise click.BadParameter(f"Invalid event type: {val}", ctx, param)
        ev_list.append(val)
    return ev_list


def str2gender(ctx, param, val: str) -> Gender:
    if isinstance(val, Gender):
        return val
    try:
        return Gender[val.upper()]
    except KeyError:
        raise click.BadParameter(f"Invalid gender: {val}", ctx, param)


def str2date(ctx, param, val: Union[str, datetime.date]) -> Optional[datetime.date]:
    if val is None:
        if param.required:
            raise click.BadParameter(f"You must specify a date", ctx, param)
        return val
    if val is None or isinstance(val, datetime.date):
        return val
    return datetime.datetime.strptime(val, "%Y-%m-%d").date()


def pos_int(ctx, param, val: int):
    if val < 1:
        raise click.BadParameter(f"value must be positive", ctx, param)
    return val


@click.command("check recent race status")
@click.option(
    "--event", "-e", "events", multiple=True, callback=str2event, help="show specific event type(s)"
)
@click.option("--speed", is_flag=True, help="show Super G and Downhill")
@click.option("--tech", is_flag=True, help="show Slalom and GS")
@click.option(
    "--gender",
    callback=str2gender,
    default=Gender.All,
    help="show events for just M or F",
)
@click.option("--summarize/--no-summarize", default=True, help="show race summary")
@click.option(
    "--top", type=int, default=5, callback=pos_int, help="summarize race by the top X finishers"
)
@click.option("--show-top", is_flag=True, help="show the top finishers in the summary")
@click.option("--min-date", callback=str2date, help="show events on or after this date")
@click.option(
    "--max-date",
    callback=str2date,
    default=datetime.date.today(),
    help="show events up to this day",
    show_default=True,
)
@click.option(
    "--num-days",
    type=int,
    callback=pos_int,
    default=7,
    help="show events for days leading up to --max-date",
    show_default=True,
)
@click.option("--skip-cache", is_flag=True, help="Fetch new data from the fis website")
@click.pass_context
def main(
    ctx: click.Context,
    events: List[Event],
    speed: bool,
    tech: bool,
    gender: Gender,
    summarize: bool,
    top: int,
    show_top: bool,
    min_date: Optional[datetime.date],
    max_date: datetime.date,
    num_days: int,
    skip_cache: bool,
):
    # breakpoint()
    date_range = datetime.timedelta(days=num_days)
    if min_date is None:
        min_date = max_date - date_range

    if speed:
        events.extend([Event.SG, Event.DH])
    if tech:
        events.extend([Event.SL, Event.GS])
    event_filter = set(events)

    cal = Calendar()
    cal_events = cal.scan(skip_cache=skip_cache)
    for ev in cal_events:
        if ev.dates[0] < min_date:
            continue
        elif ev.dates[0] > datetime.date.today():
            break
        elif ev.gender not in gender:
            continue
        elif event_filter and not any([e in event_filter for e in ev.events]):
            continue

        rf = RaceFilter(status=Status.ResultsAvailable)
        ev_races = ev.races(skip_cache=skip_cache, f=rf)
        if ev_races:
            print(ev.place)
            for er in ev_races:
                print(f"{er.date} - {er.event} ({er.gender})")
                if summarize:
                    er.summarize(top=top, show_top=show_top)
            print()


if __name__ == "__main__":
    main()
