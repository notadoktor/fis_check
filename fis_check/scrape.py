#!/usr/bin/env python3

import datetime
import logging
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, cast
from urllib.parse import parse_qsl, urlencode, urlparse

import requests
from bs4 import BeautifulSoup
from bs4.element import NavigableString, PageElement, Tag

from .enums import Category, Country, EventType, Gender, RunStatus, SectorCode, Status
from .util import Cache, RaceFilter, merge_status, tz_cet, tz_local

hidden_class = r"hidden-[^-\s]+?-up"

TODAY = datetime.date.today()
DEFAULT_SEASON = str(TODAY.year) if TODAY.month < 9 else str(TODAY.year + 1)
DEFAULT_SECTORCODE = SectorCode.AL
DEFAULT_CATEGORY = Category.WC


class EventNotFound(Exception):
    def __init__(
        self, event_id: str, season_code: str, sector_code: SectorCode, msg: Optional[str] = None
    ) -> None:
        if msg is None:
            msg = f"Unable to find an event matching event_id={event_id} season_code={season_code} sector_code={sector_code}"
        super().__init__(msg)
        self.event_id = event_id
        self.season_code = season_code
        self.sector_code = sector_code


class RaceNotFound(Exception):
    pass


class ResultNotFound(Exception):
    pass


class RacerNotFound(Exception):
    pass


# TODO: replace with mixin for scrape objects that handles caching / fetching with self values
def get_body(
    url: str, params: Dict[str, Any] = {}, cache: Optional[Cache] = None, skip_cache: bool = False
) -> BeautifulSoup:
    str_params = {str(k): str(v) for k, v in params.items()}
    if params:
        url_param_str = f"{url}?{urlencode(params)}"
    else:
        url_param_str = url
    if cache is None:
        parsed = urlparse(url)
        if parsed.path[1:]:
            cache_key = urlparse(url).path[1:].replace("/", "_")
        else:
            cache_key = parsed.netloc
        cache = Cache(f"{cache_key}_raw", params=str_params)

    if not skip_cache and not cache.expired:
        logging.debug(f"loading cached data for {url_param_str}")
        body_text = cache.load()
    else:
        logging.debug(f"fetching new data for {url_param_str}")
        resp = requests.get(url, params=str_params)
        if not resp.ok:
            logging.error(f"{resp.status_code}: {resp.text}")
            exit(1)
        body_text = resp.text
        logging.debug(f"writing data to {cache.path}")
        cache.write(body_text)

    return BeautifulSoup(body_text, "lxml")


def visible_a(tag) -> bool:
    return (
        tag
        and tag.name == "a"
        and (
            not tag.has_attr("class") or not any([re.match(hidden_class, c) for c in tag["class"]])
        )
    )


def visible_div(tag: Optional[Tag]):
    return (
        bool(tag)
        and tag.name == "div"
        and (
            not tag.has_attr("class") or not any([re.match(hidden_class, c) for c in tag["class"]])
        )
    )


def get_comp_id(url: str) -> str:
    """pulls the competitor ID out of the url from a race result row"""
    parts = urlparse(url)
    qs = dict(parse_qsl(parts.query))
    return qs["competitorid"]


class Calendar:
    url: str = "https://www.fis-ski.com/DB/alpine-skiing/calendar-results.html"

    def __init__(
        self,
        season_code: str = DEFAULT_SEASON,
        sector_code: SectorCode = DEFAULT_SECTORCODE,
        categorycode: Category = DEFAULT_CATEGORY,
        autoload: bool = True,
    ) -> None:
        self.season_code = season_code
        self.sector_code = sector_code
        self.categorycode = categorycode
        self.cache = Cache("calendar")
        self.form_cache = Cache(
            "calendar_form", ctype="json", expire_after=datetime.timedelta(days=90)
        )
        self.event_cache = Cache("calendar_events")
        self._events: List["Event"] = []
        self._options: Dict[str, Any] = {}

        if autoload:
            self.scan()

    @property
    def options(self):
        if not self._options:
            self._load_options()
        return self._options

    def _build_query(self, **opts) -> Dict[str, str]:
        cal_qs = {
            "sector_code": self.sector_code,
            "seasoncode": self.season_code,
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
        if self.form_cache.expired or skip_cache:
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

            assert isinstance(form, Tag)

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
        else:
            self._options = self.form_cache.load()

    def parse_date(self, date_tag: Tag) -> List[datetime.date]:
        if date_tag.string is None:
            # end/beginning of month
            try:
                assert len(list(date_tag.stripped_strings)) == 2, f"Unexpected values in date tag"
                min_str, max_str = [d.replace("-", "") for d in date_tag.stripped_strings]
                logging.debug(f"Split month: {min_str}-{max_str}")
                max_date = datetime.datetime.strptime(max_str, "%d %b %Y").date()
                min_day, min_month = min_str.split()
                min_year = (
                    max_date.year - 1 if min_month == 12 and max_date.month == 1 else max_date.year
                )
                min_date = datetime.datetime.strptime(
                    f"{min_day} {min_month} {min_year}", "%d %b %Y"
                ).date()
                assert min_date < max_date, f"min_date is after max_date, check parser"
            except AssertionError as e:
                logging.error(str(e))
                breakpoint()
                raise e
        else:
            # one or multiple days in the same month
            date_str = str(date_tag.string)
            logging.debug(f"Same month: {date_str}")
            days, month, year = date_str.split()
            if "-" in days:
                min_day, max_day = days.split("-")
                min_date = datetime.datetime.strptime(
                    f"{min_day} {month} {year}", "%d %b %Y"
                ).date()
                max_date = datetime.datetime.strptime(
                    f"{max_day} {month} {year}", "%d %b %Y"
                ).date()
            else:
                min_date = max_date = datetime.datetime.strptime(
                    f"{days} {month} {year}", "%d %b %Y"
                ).date()

        date_list = []
        logging.debug(f"filling range {min_date} - {max_date}")
        curr_dt = min_date
        while curr_dt <= max_date:
            date_list.append(curr_dt)
            if len(date_list) >= 2 and date_list[-2] == date_list[-1]:
                print("infinite loop bitch")
                breakpoint()
                pass
            curr_dt += datetime.timedelta(days=1)
        return date_list

    def get_event(self, event_id: str) -> Optional["Event"]:
        for e in self._events:
            if e.id == event_id:
                return e

    def scan(self, skip_cache: bool = False, **kwargs) -> List["Event"]:
        cal_qs = self._build_query(**kwargs)
        self.event_cache.params = cal_qs.copy()

        if self.event_cache.expired or skip_cache:
            logging.debug(
                f"scraping new data, event_cache.expired={self.event_cache.expired}, skip_cache={skip_cache}"
            )
            cal_page = get_body(self.url, cal_qs, skip_cache=skip_cache)
            cal = cal_page.find(
                "div", attrs={"id": "calendarloadcontainer", "class": "section__body"}
            )
            assert isinstance(cal, Tag)
            header_obj = cast(
                Tag, cal.find("div", attrs={"class": "table__head"})
            ).div.div.div.children
            assert isinstance(header_obj, Tag)

            cal_header = [d.string for d in header_obj.div.div.div.children if visible_div(d)]  # type: ignore

            cal_body = cast(Tag, cal.find("div", attrs={"id": "calendardata", "class": "tbody"}))
            events: List[Event] = []
            for cal_row in cal_body.children:
                if cal_row.name != "div":
                    continue
                assert isinstance(cal_row, Tag)
                row_data = cast(Tag, cast(Tag, cal_row).find("div", attrs={"class": "g-row"}))
                event_raw = dict(zip(cal_header, [c for c in row_data.children if visible_a(c)]))
                event_data: dict[str, Any] = {"id": cal_row["id"]}
                logging.debug(f"processing event_id {event_data['id']}")
                event_data["status"] = merge_status(
                    [s["title"] for s in event_raw["Status"].find_all("span")]
                )
                logging.debug(f"status: {event_data['status']}")

                event_data["dates"] = self.parse_date(event_raw["Date"])
                logging.debug(f"dates: {', '.join([str(dt) for dt in event_data['dates']])}")
                if event_data["dates"][0] > datetime.date.today():
                    logging.debug(f"start date is in the future, ending scan")
                    break

                event_data["place"] = str(event_raw["Place"].div.string)
                logging.debug(f"place: {event_data['place']}")
                event_data["country"] = Country[
                    event_raw["Country"].find("span", attrs={"class": "country__name-short"}).string
                ]
                logging.debug(f"country: {event_data['country']}")

                event_data["sector_code"] = SectorCode[event_raw["Disc."].string]
                logging.debug(f"sector_code: {event_data['sector_code']}")
                cats, evs = [
                    d.div.string
                    for d in event_raw["Category & Event"].div.contents
                    if d.name == "div"
                ]
                if " • " in cats:
                    event_data["categories"] = [Category[k] for k in cats.split(" • ")]
                else:
                    event_data["categories"] = [Category[cats]]
                logging.debug(
                    f"categories: {', '.join([str(c) for c in event_data['categories']])}"
                )

                for ev_sep in [" • ", " "]:
                    if not event_data.get("event_types") and ev_sep in evs:
                        event_data["event_types"] = [
                            EventType[re.sub(r"^\dx", "", k)] for k in evs.split(ev_sep)
                        ]
                if not event_data.get("event_types"):
                    try:
                        event_data["event_types"] = [EventType[re.sub(r"^\dx", "", evs)]]
                    except KeyError:
                        breakpoint()
                        raise
                logging.debug(
                    f"event_types: {', '.join([str(et) for et in event_data['event_types']])}"
                )

                event_data["gender"] = Gender[event_raw["Gender"].div.div.div.string]
                logging.debug(f"gender: {event_data['gender']}")
                new_event = Event(from_calendar=True, skip_cache=skip_cache, **event_data)
                events.append(new_event)
            self._events = events
            self.event_cache.write(self._events)
        else:
            self._events = self.event_cache.load()
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


class Event:
    url: str = "https://www.fis-ski.com/DB/general/event-details.html"
    id: str
    dates: List[datetime.date]
    place: str
    country: Country
    categories: Sequence[Category]
    event_types: Sequence[EventType]
    gender: Gender
    season_code: str
    sector_code: SectorCode
    status: Status

    def __init__(
        self,
        id: str,
        season_code: str = DEFAULT_SEASON,
        sector_code: SectorCode = DEFAULT_SECTORCODE,
        skip_cache: bool = False,
        from_calendar: bool = False,
        **kwargs,
        # dates: List[datetime.date] = None,
        # place: Optional[str] = None,
        # country: Optional[Country] = None,
        # categories: Sequence[Category] = None,
        # event_types: Sequence[EventType] = None,
        # gender: Optional[Gender] = None,
        # season_code: str = DEFAULT_SEASON,
        # sector_code: SectorCode = SectorCode.AL,
        # status: Status = Status(0),
    ) -> None:
        self.id = id
        self.season_code = season_code
        self.sector_code = sector_code
        self._races = self._load_races(skip_cache)

        if from_calendar:
            # if any fields are missing, exception should throw
            self.dates = sorted(set(kwargs["dates"]))
            self.place = kwargs["place"]
            self.country = kwargs["country"]
            self.categories = sorted(set(kwargs["categories"]))
            self.event_types = sorted(set(kwargs["event_types"]))
            self.gender = kwargs["gender"]
            self.status = kwargs["status"]
        else:
            # fetch and load details from the event page
            url_params = {
                "eventid": self.id,
                "seasoncode": self.season_code,
                "sectorcode": str(self.sector_code),
            }
            event_body = get_body(self.url, url_params, skip_cache=skip_cache)
            self.place = event_body.find("h1", attrs={"class": "event-header__name"}).string.strip()  # type: ignore
            country = re.search(r"\(([A-Z]{3})\)$", self.place)
            if country:
                self.country = Country[country.group(1)]

            # the rest is contained in the race objects
            if len(self._races) == 0:
                raise EventNotFound(self.id, self.season_code, self.sector_code)

            event_genders = set()
            event_dates = set()
            event_cats = set()
            event_ets = set()
            self.status = Status(0)
            for r in self._races:
                event_genders.add(r.gender)
                event_dates.add(r.date)
                event_cats.add(r.category)
                event_ets.add(r.event_type)
                self.status |= r.status

            self.gender = event_genders.pop() if len(event_genders) == 1 else Gender.ALL
            self.dates = sorted(event_dates)
            self.categories = sorted(event_cats)
            self.event_types = sorted(event_ets)

    @property
    def races(self) -> List["Race"]:
        self.load_races()
        return self._races

    def filter_races(self, f: RaceFilter) -> List["Race"]:
        self.load_races()
        return [r for r in self._races if r.filtered(f)]

    # def update(self) -> "Event":
    #     """ returns a new, possibly updated Event object """
    #     return self.__class__(self.id, self.season_code, self.sector_code, True)

    def load_races(self, skip_cache: bool = False):
        if not self._races or skip_cache:
            self._races = self._load_races(skip_cache)

    def _load_races(self, skip_cache: bool = False) -> List["Race"]:
        event_qs = {
            "sectorcode": str(self.sector_code),
            "seasoncode": self.season_code,
            "eventid": self.id,
        }

        event_page = get_body(self.url, event_qs, skip_cache=skip_cache)
        race_table = event_page.find("div", attrs={"class": "table_pb"})
        assert isinstance(race_table, Tag)
        header_obj, subheader_obj = [
            d.div.div for d in race_table.find_all("div", attrs={"class": "thead"})
        ]
        header = [
            d.string if d.string else d.div.string for d in header_obj.children if visible_div(d)
        ]
        runs_header = [
            str(d.string).strip().lower()
            for d in subheader_obj.find("div", attrs={"class": "g-row"}).children
            if d.name == "div"
        ]

        all_races: List[Race] = []
        body_obj = race_table.find("div", attrs={"class": "table__body"})
        assert isinstance(body_obj, Tag)
        for day_obj in [d.div.div.div for d in body_obj.children if d.name == "div"]:  # type: ignore
            race_raw = dict(
                zip(header, [tag for tag in day_obj.children if visible_a(tag) or visible_div(tag)])
            )

            race_args: Dict[str, Any] = {
                "sector_code": self.sector_code,
                "event_id": self.id,
            }

            race_args["id"] = dict(parse_qsl(urlparse(day_obj.a["href"]).query))["raceid"]
            race_args["status"] = merge_status(
                [s["title"] for s in race_raw["Status"].find_all("span")]
            )
            raw_date_str: str = race_raw["Date"].div.div.div.string
            try:
                date_str = datetime.datetime.strptime(raw_date_str, "%d %b %Y")
            except ValueError:
                try:
                    date_str = datetime.datetime.strptime(raw_date_str, "%d %b")
                except ValueError:
                    logging.error(f"Cannot parse date: {raw_date_str}s")
                    raise

            race_args["date"] = date_str.replace(year=int(self.season_code)).date()

            if race_args["date"].month > 7:
                race_args["date"] = race_args["date"].replace(year=race_args["date"].year - 1)

            # if <a>, no live result link, just a bare codex string
            if race_raw["Codex"].name == "a":
                race_args["codex"] = str(race_raw["Codex"].string)
            else:
                # if <div>, save link result URL and extract codex from deeper divs
                race_args["live_url"] = race_raw["Codex"].a["href"]
                race_args["codex"] = str(race_raw["Codex"].a.div.div.div.string)
            ev_type: str = list(race_raw["Event"].stripped_strings)[0]
            if ev_type not in EventType.__members__.values():
                logging.info(f"Unknown event type: {ev_type}")
                continue
            race_args["event_type"] = EventType(ev_type)
            race_args["category"] = Category[race_raw["Category"].string]
            gender_str = list(race_raw["Gender"].stripped_strings)[0]
            if gender_str not in Gender.__members__.keys():
                logging.info(f"Unknown gender value: {gender_str}")
                breakpoint()
                raise
            race_args["gender"] = Gender[gender_str]
            all_run_info = list(race_raw["Runs"].find_all("div", attrs={"class": "g-row"}))
            if all_run_info:
                race_args["runs"] = []
                for run_info in all_run_info:
                    run_raw: Dict[str, str] = dict(
                        zip(
                            runs_header,
                            [
                                d.string.strip() if d.string else ""
                                for d in run_info.children
                                if d.name == "div"
                            ],
                        )
                    )

                    run = dict()
                    run["race_id"] = race_args["id"]
                    run["run"] = int(re.sub(r"\D", "", run_raw["run"]))

                    if run_raw["cet"] and ":" in run_raw["cet"]:
                        cet_hour, cet_minute = [int(t) for t in run_raw["cet"].split(":")]
                        run["cet"] = datetime.time(cet_hour, cet_minute, tzinfo=tz_cet)
                    else:
                        run["cet"] = None

                    if run_raw["loc"] and ":" in run_raw["loc"]:
                        loc_hour, loc_minute = [int(t) for t in run_raw["loc"].split(":")]
                        run["loc"] = datetime.time(loc_hour, loc_minute, tzinfo=tz_local)
                    else:
                        run["loc"] = None

                    if run_raw.get("status"):
                        run["status"] = RunStatus[run_raw["status"].title().replace(" ", "")]
                    else:
                        run["status"] = None

                    race_args["runs"].append(RaceRun(**run))
            else:
                race_args["runs"] = []
            race_args["comments"] = (
                str(race_raw["Comments"].string)
                if race_raw.get("Comments") and race_raw["Comments"].string
                else ""
            )

            all_races.append(Race(**race_args))
        return all_races


class Race:
    def __init__(
        self,
        id: str,
        event_id: str,
        category: Category,
        codex: str,
        date: datetime.date,
        event_type: EventType,
        gender: Gender,
        status: Status,
        runs: List["RaceRun"],
        comments: Optional[str] = None,
        live_url: Optional[str] = None,
        sector_code: SectorCode = DEFAULT_SECTORCODE,
    ) -> None:
        self.id = id
        self.category = category
        self.codex = codex
        self.date = date
        self.event_id = event_id
        self.event_type = event_type
        self.gender = gender
        self.status = status
        self.comments = comments
        self.live_url = live_url
        self.runs = runs
        self.sector_code = sector_code
        self._results: List["RaceResult"] = []

    def __repr__(self) -> str:
        return f"<Race id={self.id} eid={self.event_id} date={self.date} event={self.event_type} gender={self.gender}>"

    def filtered(self, f: RaceFilter) -> bool:
        if f.category and self.category != f.category:
            logging.debug(f"{self} failed category filter: {self.category} != {f.category}")
            return False
        if len(f.event_types) and self.event_type not in f.event_types:
            ef_str = ", ".join(sorted([str(ef) for ef in f.event_types]))
            logging.debug(f"{self} failed event_type filter: {self.event_type} in ({ef_str})")
            return False
        if f.min_date and self.date < f.min_date:
            logging.debug(f"{self} failed min_date filter: {self.date}")
            return False
        if f.max_date and self.date > f.max_date:
            logging.debug(f"{self} failed max_date filter: {self.date}")
            return False
        if f.gender and self.gender not in f.gender:
            logging.debug(f"{self} failed gender filter: {self.gender.name} in {f.gender.name}")
            return False
        if f.live_url is not None:
            if f.live_url != bool(self.live_url):
                logging.info(f"{self} failed live_url filter")
                return False
        if Status.CANCELLED & self.status and (not f.status or Status.CANCELLED not in f.status):
            logging.info(f"{self} failed: cancelled")
            return False
        if f.status and not self.status & f.status:
            logging.debug(f"{self} failed status filter: {self.status} & {f.status}")
            breakpoint()
            return False
        return True

    def results(self, top: int = 10, skip_cache: bool = False) -> List["RaceResult"]:
        if Status.CANCELLED in self.status:
            logging.error(f"No results, race was cancelled")
            return []

        self.load_results(True)
        if len(self._results) >= top:
            return self._results[:top]
        else:
            logging.warning(
                f"Could not return top {top} results, returning all {len(self._results)}"
            )
            return self._results

    def load_results(self, skip_cache: bool = False):
        if not self._results or skip_cache:
            qs = {"raceid": self.id, "sectorcode": str(self.sector_code)}
            result_body = get_body(RaceResult.url, qs)

            result_table = cast(Tag, result_body.find("div", id="events-info-results")).div
            result_rows: list[PageElement] = [a for a in result_table.children if a.name == "a"]
            if self.event_type.single_run:
                header = SPEED_HEADER
            else:
                header = TECH_HEADER
            all_results = []
            for row in result_rows:
                row_cols = row.div.div
                row = dict(
                    zip(header, [d.stripped_strings for d in row_cols.children if d.name == "div"])
                )
                rr_attrs: Dict[str, Any] = dict()
                rr_attrs["race_id"] = self.id
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

            dq_ranks = {"DNF": 990, "DNS": 999}
            disqualified = dict(
                zip(
                    ["DNF", "DNS"],
                    [
                        d.div
                        for d in result_table.parent.next_siblings  # type: ignore
                        if d.name == "div" and "table__body" in d["class"]
                    ],
                )
            )
            for dq_type in disqualified:
                dq_list = [
                    a.div.div
                    for a in disqualified[dq_type].children
                    if a.name == "a" and "table-row" in a["class"]
                ]
                for row in dq_list:
                    cols = [
                        list(d.stripped_strings)[0]
                        for d in row.children
                        if d.name == "div" and list(d.stripped_strings)
                    ]
                    bib, fis_code, name, birth_year, nation = cols[:5]

                    rr_attrs: Dict[str, Any] = {
                        "race_id": self.id,
                        "rank": dq_ranks[dq_type],
                        "time": dq_type,
                        "difference": "",
                    }
                    rr_attrs["bib"] = int(bib)
                    rr_attrs["fis_code"] = fis_code
                    rr_attrs["name"] = name
                    rr_attrs["birth_year"] = int(birth_year)
                    rr_attrs["nation"] = nation
                    # rr_attrs["racer_id"] = get_comp_id(row.parent.parent["href"])
                    rr = RaceResult(**rr_attrs)
                    all_results.append(rr)

            self._results = all_results

    def dq(self, skip_cache: bool = False) -> List["RaceResult"]:
        self.load_results(skip_cache)
        return [r for r in self._results if r.rank > 900]

    def dnf(self, skip_cache: bool = False) -> List["RaceResult"]:
        self.load_results(skip_cache)
        return [r for r in self._results if r.rank == 990]

    def dns(self, skip_cache: bool = False) -> List["RaceResult"]:
        self.load_results(skip_cache)
        return [r for r in self._results if r.rank == 999]


SPEED_HEADER = [
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
TECH_HEADER = [
    "rank",
    "bib",
    "FIS code",
    "name",
    "birth year",
    "nation",
    "run 1",
    "run 2",
    "tot. time",
    "diff. time",
    "FIS points",
    "cup points",
]


class RaceRun:
    run: int
    race_id: str
    cet: Optional[datetime.time]
    loc: Optional[datetime.time]
    status: Optional[RunStatus]
    info: Optional[str]

    def __init__(
        self,
        run: int,
        race_id: str,
        cet: Optional[datetime.time] = None,
        loc: Optional[datetime.time] = None,
        status: Optional[RunStatus] = None,
        info: Optional[str] = None,
    ) -> None:
        self.run = run
        self.race_id = race_id
        self.cet = cet
        self.loc = loc
        self.status = status
        self.info = info


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
    url: str = "https://www.fis-ski.com/DB/general/results.html"

    def __init__(
        self,
        race_id: str,
        rank: int,
        bib: int,
        time: str,
        difference: str,
        name: str,
        nation: Country,
        fis_points: Optional[float] = None,
        cup_points: Optional[int] = None,
        racer_id: Optional[str] = None,
        birth_year: Optional[int] = None,
        fis_code: Optional[str] = None,
        racer: Optional[Racer] = None,
    ) -> None:
        self.rank = rank
        self.race_id = race_id
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
