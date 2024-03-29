import datetime
import json
import logging
from typing import List, Optional, Union

import click

from . import scrape
from .enums import EventType, Gender, RunStatus, Status
from .util import RaceFilter


def str2event(ctx, param, val_list: str) -> List[EventType]:
    ev_list = []
    for val in val_list:
        if not isinstance(val, EventType):
            try:
                val = EventType[val.upper()]
            except KeyError:
                raise click.BadParameter(f"Invalid event type: {val}", ctx, param)
        ev_list.append(val)
    return ev_list


def str2gender(ctx, param, val: Union[str, Gender]) -> Gender:
    if not val:
        return Gender.ALL

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
    help="show events for just M or F",
)
@click.option("--summarize/--no-summarize", default=True, help="show race summary")
@click.option(
    "--top", type=int, default=3, callback=pos_int, help="summarize race by the top X finishers"
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
    help="show events for days leading up to and including --max-date",
    show_default=True,
)
@click.option("--skip-cache", is_flag=True, help="Fetch new data from the fis website")
@click.option("--verbose", "-v", "log_level", flag_value=logging.INFO, help="set log level to info")
@click.option("--debug", "-D", "log_level", flag_value=logging.DEBUG, help="set log level to debug")
@click.pass_context
def main(
    ctx: click.Context,
    events: List[EventType],
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
    log_level: int,
):
    if log_level:
        logging.getLogger("root").setLevel(log_level)
        logging.debug(f"params: {json.dumps({k: repr(v) for k, v in ctx.params.items()})}")
    date_range = datetime.timedelta(days=num_days)
    if min_date is None:
        min_date = max_date - date_range

    if speed:
        events.extend([EventType.SG, EventType.DH])
    if tech:
        events.extend([EventType.SL, EventType.GS])
    event_filter = set(events)

    cal = scrape.Calendar()
    cal_events = cal.scan(skip_cache=skip_cache)
    logging.debug(f"Got {len(cal_events)} events")
    # breakpoint()
    for ev in cal_events:
        if all([d < min_date for d in ev.dates]):
            logging.debug(f"skipping {ev.id}, all dates < {min_date}: {[str(d) for d in ev.dates]}")
            continue
        elif all([d > max_date for d in ev.dates]):
            logging.info(f"breaking at {ev.id}, all dates > {max_date}")
            # max_date defaults to today, if overridden assume intentional
            break
        elif ev.gender not in gender:
            logging.debug(f"skipping {ev.id}, failed {ev.gender.name} in {gender.name}")
            continue
        elif event_filter and not any([e in event_filter for e in ev.event_types]):
            ef_str = ", ".join(sorted([str(ef) for ef in event_filter]))
            et_str = ", ".join(sorted([str(et) for et in ev.event_types]))
            logging.debug(f"skipping {ev.id}, failed event filter ({et_str}) ^ ({ef_str})")
            continue

        rf = RaceFilter(
            status=Status.RESULTS_AVAILABLE | Status.PDF_AVAILABLE, event_types=event_filter
        )
        ev_races = ev.filter_races(f=rf)
        if ev_races:
            print(ev.place)
            for er in ev_races:
                er_info = [str(er.date), str(er.gender), er.event_type.value]
                if len(er.runs) and Status.CANCELLED not in er.status:
                    if not all(
                        [not r.status or r.status == RunStatus.OfficialResults for r in er.runs]
                    ):
                        run_info = []
                        for run in er.runs:
                            if run.status:
                                run_info.append(f"run{run.run}: {run.status}")
                                if run.cet:
                                    run_info[-1] += f" @ {run.cet.isoformat('minutes')}"
                        if run_info:
                            er_info.extend(run_info)
                if er.comments:
                    er_info.append(er.comments.strip())
                print(" - ".join(er_info))
                if summarize and all(
                    [r.status and r.status == RunStatus.OfficialResults for r in er.runs]
                ):
                    summarize_race(er, top=top, show_top=show_top)
            print()
        else:
            logging.info(f"no races in {ev} passed RaceFilter: {rf}\n")
            # breakpoint()
            # ev.filter_races(f=rf)
            pass


def summarize_race(race: scrape.Race, top: int = 5, show_top: bool = False) -> None:
    max_bin = 0
    for r in race.results(top=top):
        if show_top:
            print(str(r))
        if r.bin > max_bin:
            max_bin = r.bin
    print(f"DQ: {len(race.dq())} (DNF: {len(race.dnf())}, DNS: {len(race.dns())})")
    print(f"Max bin: {max_bin}")
    print()
