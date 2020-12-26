import datetime
import json
import pickle
from base64 import b64encode
from pathlib import Path
from typing import Callable, Dict, NamedTuple, Optional, Union, Literal, List, Any

from enums import Category, Status, Event, Gender


class RaceFilter(NamedTuple):
    category: Category = Category.WC
    codex: Optional[str] = None
    comments: Optional[bool] = None
    date: Optional[datetime.date] = None
    event: Optional[Event] = None
    gender: Optional[Gender] = None
    live_url: Optional[bool] = None
    status: Optional[Status] = Status.ResultsAvailable


class BaseObject:
    id: str
    seasoncode: str = "2021"

    def __init__(self, id: str, **kwargs) -> None:
        self.id = id
        for key in kwargs:
            if hasattr(self, key):
                setattr(self, key, kwargs[key])
            else:
                raise KeyError(f"Invalid attribute: {key}")


class Cache:
    root_dir: Path = Path("~/.cache/fis_check").expanduser()
    key: str = None  # type: ignore
    expire_in: datetime.timedelta = datetime.timedelta(days=1)
    params: Optional[Dict[str, str]] = None
    ctype: Literal["pickle", "json"] = "pickle"

    def __init__(self, key: str, **kwargs) -> None:
        self.key = key

        for k in kwargs:
            if hasattr(self, k):
                setattr(self, k, kwargs[k])
            else:
                raise KeyError(f"Invalid parameter: {k}")

    @property
    def expired(self) -> bool:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return True
        if (
            datetime.datetime.fromtimestamp(self.path.stat().st_mtime)
            < datetime.datetime.now() - self.expire_in
        ):
            return True
        return False

    @property
    def filename(self) -> str:
        if self.params:
            id_str = b64encode(
                "&".join([f"{k}={v}" for k, v in self.params.items()]).encode("utf-8"),
                b"_-",
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
            fmt = json.dumps  # type: ignore

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