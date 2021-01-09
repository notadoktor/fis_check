import datetime
import json
import pickle
from base64 import b64encode
from pathlib import Path
from typing import Any, Dict, List, Literal, NamedTuple, Optional
from urllib.parse import urlparse

import pytz

from .enums import Category, EventType, Gender, RunStatus, Status

cache_dir = Path("~/.cache/fis_check").expanduser()
tz_cet: datetime.tzinfo = pytz.timezone("cet")
tz_local: datetime.tzinfo = datetime.datetime.now().astimezone().tzinfo  # type: ignore


class RaceFilter(NamedTuple):
    category: Category = Category.WC
    event_types: set[EventType] = set()
    min_date: Optional[datetime.date] = None
    max_date: Optional[datetime.date] = None
    gender: Optional[Gender] = None
    live_url: Optional[bool] = None
    status: Optional[Status] = Status.ResultsAvailable


class RaceRun(NamedTuple):
    run: int
    race_id: str
    cet: Optional[datetime.time]
    loc: Optional[datetime.time]
    status: Optional[RunStatus]
    info: Optional[str] = None


class Cache:
    root_dir: Path
    key: str
    expire_after: datetime.timedelta
    ctype: Literal["pickle", "json"]
    params: Optional[Dict[str, str]]

    def __init__(
        self,
        key: str = None,
        url: str = None,
        root_dir: Path = cache_dir,
        expire_after: datetime.timedelta = datetime.timedelta(days=1),
        params: Dict[str, str] = None,
        ctype: Literal["pickle", "json"] = "pickle",
    ) -> None:
        if key:
            self.key = key
        elif url:
            parsed = urlparse(url)
            if parsed.path[1:]:
                self.key = urlparse(url).path[1:].replace("/", "_")
            else:
                self.key = parsed.netloc
        else:
            raise KeyError("You must specify key or url")
        self.root_dir = root_dir
        self.ctype = ctype
        self.expire_after = expire_after
        self.params = params

    @property
    def age(self) -> datetime.timedelta:
        if not self.path.exists():
            raise OSError(f"Cache file {self.path} does not exist")
        mtime = datetime.datetime.fromtimestamp(self.path.stat().st_mtime)
        return datetime.datetime.now() - mtime

    @property
    def expired(self) -> bool:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return True
        if self.age > self.expire_after:
            return True
        return False

    @property
    def filename(self) -> str:
        if self.params:
            id_str = b64encode(
                "&".join([f"{k}={v}" for k, v in self.params.items()]).encode("utf-8"), b"_-",
            ).decode("utf-8")
            return f"{self.key}_{id_str}"
        return self.key

    @property
    def path(self):
        return self.root_dir / self.filename

    def exists(self):
        return self.path.exists()

    def load(self, as_str: bool = False):
        contents = self.path.read_bytes()
        if self.ctype == "pickle":
            contents = pickle.loads(contents)
        else:
            contents = json.loads(contents)

        if as_str:
            return contents.encode("utf-8")
        else:
            return contents

    def write(self, val: Any):
        if self.ctype == "pickle":
            mode = "wb"
            fmt = pickle.dumps
        elif self.ctype == "json":
            mode = "wt"
            fmt = json.dumps
        else:
            raise ValueError(f"Invalid format: {self.ctype}")

        with self.path.open(mode) as fh:
            fh.write(fmt(val))


def merge_status(status_list: List[str]) -> Status:
    s = Status(0)
    for s_str in status_list:
        try:
            new_stat = Status[s_str.title().replace(" ", "")]
        except KeyError:
            continue
        s |= new_stat
    return s
