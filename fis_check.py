#!/usr/bin/env python3

import datetime
import json
import logging
import pickle
import re
from base64 import b64decode, b64encode
from collections import defaultdict
from functools import wraps
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import parse_qsl, urlencode, urlparse

import bs4.element
import requests
from bs4 import BeautifulSoup
from requests.models import stream_decode_response_unicode

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class Event:
    pass


class Day:
    pass


class RaceResult:
    pass


# globals / defaults

base_url = "https://www.fis-ski.com/DB"
url_targets = {
    "calendar": f"{base_url}/alpine-skiing/calendar-results.html",
    "event_details": f"{base_url}/general/event-details.html",  # needs sectorcode, eventid, seasoncode
    "race_results": f"{base_url}/general/results.html",  # sectorcode, raceid
}
cache_dir = Path("~/.cache/fis_check").expanduser()

# funcs


def joinqs(base_url: str, query_opts: Dict[str, str] = {}):
    query_str = urlencode(query_opts, True)
    if query_str:
        return "?".join([base_url, query_str])
    return base_url


def cache_expired(cache: Path, limit: datetime.timedelta = datetime.timedelta(days=1)) -> bool:
    if not cache.exists() or cache.stat().st_size == 0:
        return True
    if datetime.datetime.fromtimestamp(cache.stat().st_mtime) < datetime.datetime.now() - limit:
        return True
    return False


def cache_write(cache: Path, val: Union[str, bytes]):
    if not cache.is_absolute():
        cache = cache_dir / cache
    if not cache.parent.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(val, str):
        mode = "wt"
    else:
        mode = "wb"
    with cache.open(mode) as fh:
        fh.write(val)


def cache_load(cache: Path):
    if not cache.is_absolute():
        cache = cache_dir / cache
    if not cache.exists():
        raise OSError(f"Cannot load empty cache {cache}")
    return cache.read_bytes()


def calendar_options(use_cache=True):
    cache = Path("calendar_form.json")
    if use_cache and not cache_expired(cache):
        return json.loads(cache_load(cache))

    resp = requests.get(url_targets["calendar"])
    if not resp.ok:
        logging.error(f"{resp.status_code}: {resp.text}")
        exit(1)
    bs = BeautifulSoup(resp.text, "lxml")

    calendar_form = defaultdict(dict)
    form = bs.find("form", attrs={"id": "calendar-filter"})
    if form is None:
        logging.error(f"Could not find the calendar form")
        exit(1)

    # grab inputs with defaults/restrictions
    for i in form.find_all("input"):
        calendar_form[i["id"]] = {
            "type": "input",
            "default": i["value"],
            "pattern": i.get("pattern", None),
            "maxlength": i.get("maxlength", None),
        }

    # grab selects with defaults
    for sel in form.find_all("select"):
        sel_options = calendar_form[sel["id"]]
        sel_options["type"] = "select"
        if "multiple" in sel.attrs:
            sel_options["multiple"] = True
        for opt in sel.find_all("option"):
            if "disabled" in opt.attrs:
                continue
            sel_options[opt.string] = opt["value"]
            if "selected" in opt.attrs:
                sel_options["default"] = opt["value"]

    cache_write(cache, json.dumps(calendar_form))
    return calendar_form


def calendar_text(url: str, use_cache=True) -> str:
    parsed = urlparse(url)
    id_str = b64encode("&".join(sorted(parsed.query.split("&"))).encode("utf-8"), b"_-").decode(
        "utf-8"
    )
    cache = Path(f"calendar_{id_str}")
    if use_cache and not cache_expired(cache):
        return pickle.loads(cache_load(cache))

    resp = requests.get(url)
    if not resp.ok:
        logging.error(f"{resp.status_code}: {resp.text}")
        exit(1)
    cache_write(cache, pickle.dumps(resp.text))
    return resp.text


def cal_date(date_str: str) -> List[datetime.date]:
    days, month, year = date_str.split()
    min_day, max_day = [int(d) for d in days.split("-")]
    date_list = []
    for dom in range(min_day, max_day + 1):
        date_list.append(datetime.datetime.strptime(f"{dom} {month} {year}", "%d %b %Y").date())
    return date_list


def visible_a(tag) -> bool:
    return (
        tag
        and tag.name == "a"
        and (
            not tag.has_attr("class") or not re.compile(r"\bhidden-[^-\s]+?-up\b").search(str(tag))
        )
    )


def visible_div(tag) -> bool:
    return (
        tag
        and tag.name == "div"
        and (
            not tag.has_attr("class") or not re.compile(r"\bhidden-[^-\s]+?-up\b").search(str(tag))
        )
        and bool(list(tag.stripped_strings))
    )


def scan_calendar(**kwargs):
    default_kwargs = {"sector_code": "AL", "seasoncode": "2021", "categorycode": "WC"}
    default_kwargs.update(kwargs)
    url = joinqs(url_targets["calendar"], default_kwargs)

    cal_page = BeautifulSoup(calendar_text(url), "lxml")
    cal = cal_page.find("div", attrs={"id": "calendarloadcontainer", "class": "section__body"})
    cal_header = [
        d.string
        for d in cal.find("div", attrs={"class": "table__head"}).div.div.div.children
        if visible_div(d)
    ]

    cal_body = cal.find("div", attrs={"id": "calendardata", "class": "tbody"})
    events = list()
    for cal_row in cal_body.children:
        if cal_row.name != "div":
            continue
        row_data = cal_row.find("div", attrs={"class": "g-row"})
        event_raw = dict(zip(cal_header, [c for c in row_data.children if visible_a(c)]))
        event_data = {"id": cal_row["id"]}
        event_data["status"] = [s["title"] for s in event_raw["Status"].find_all("span")]
        event_data["dates"] = cal_date(event_raw["Date"].string)
        event_data["place"] = event_raw["Place"].div.string
        event_data["country"] = (
            event_raw["Country"].find("span", attrs={"class": "country__name-short"}).string
        )
        event_data["discipline"] = event_raw["Disc."].string
        event_data["category"], event_data["event"] = [
            d.div.string for d in event_raw["Category & Event"].div.contents if d.name == "div"
        ]
        event_data["gender"] = event_raw["Gender"].div.div.div.string

        events.append(event_data)

    return events


def get_event(event_id: str):
    event_qs = {"sectorcode": "AL", "seasoncode": "2021", "eventid": event_id}
    event_resp = requests.get(url_targets["event_details"], params=event_qs)
    if not event_resp.ok:
        logging.error(f"{event_resp.status_code}: {event_resp.text}")
        exit(1)
    event_page = BeautifulSoup(event_resp.text, "lxml")

    race_table = event_page.find("div", attrs={"class": "table_pb"})
    header_obj, subheader_obj = [
        d.div.div for d in race_table.find_all("div", attrs={"class": "thead"})
    ]
    header = [d.string for d in header_obj.children if visible_div(d)]
    header.insert(
        1, "Date"
    )  # gets caught in vis filter and I don't feel like finding out why right now
    runs_header = [
        d.string.strip()
        for d in subheader_obj.find("div", attrs={"class": "g-row"}).children
        if d.name == "div"
    ]

    event_races = []
    body_obj = race_table.find("div", attrs={"class": "table__body"})
    for day_obj in [d.div.div.div for d in body_obj.children if d.name == "div"]:
        day_raw = dict(zip(header, [a for a in day_obj.children if visible_a(a)]))

        day: Dict[str, Any] = {}
        day["race_id"] = dict(parse_qsl(urlparse(day_obj.a["href"]).query))["raceid"]
        day["status"] = [s["title"] for s in day_raw["Status"].find_all("span")]
        day["date"] = (
            datetime.datetime.strptime(day_raw["Date"].div.div.div.string, "%d %b")
            .replace(year=int(event_qs["seasoncode"]))
            .date()
        )
        if day["date"].month > 7:
            day["date"] = day["date"].replace(year=day["date"].year - 1)
        day["codex"] = day_raw["Codex"].string
        day["event"] = list(day_raw["Event"].stripped_strings)[0]
        day["category"] = day_raw["Category"].string
        day["gender"] = list(day_raw["Gender"].stripped_strings)[0]
        run_info = day_raw["Runs"].find("div", attrs={"class": "g-row"})
        if run_info:
            day["runs"] = dict(
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
            day["runs"] = {}
        day["comments"] = day_raw["Comments"].string if day_raw.get("Comments") else ""

        event_races.append(day)

    return event_races


def get_results(race_id: str):
    qs = {"raceid": race_id, "sectorcode": "AL"}
    resp = requests.get(url_targets["race_results"], params=qs)
    if not resp.ok:
        breakpoint()
        logging.error(f"{resp.status_code}: {resp.text}")
        exit(1)

    result_table = BeautifulSoup(resp.text).find("div", attrs={"class": "events-info-results"}).div
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
    for row in result_rows:
        row_cols = row.div.div
        row = dict(zip(header, [d.stripped_strings for d in row_cols.children if d.name == "div"]))
        breakpoint()
        pass


def main():
    # cal_events = scan_calendar()
    deets = get_event("48188")
    dh_res = get_results("107381")
    breakpoint()
    sg_res = get_results("107382")
    breakpoint()
    pass


if __name__ == "__main__":
    main()
