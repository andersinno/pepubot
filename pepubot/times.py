from datetime import datetime, timezone, tzinfo
from typing import Callable

import pytz

from .settings import get_settings


def get_default_timezone() -> tzinfo:
    return pytz.timezone(get_settings().TIMEZONE)


def now(_get_tz: Callable[[], tzinfo] = get_default_timezone) -> datetime:
    utcnow = datetime.utcnow().replace(tzinfo=timezone.utc)
    return utcnow.astimezone(_get_tz())
