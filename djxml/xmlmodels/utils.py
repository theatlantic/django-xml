from __future__ import absolute_import
import pytz
import dateutil.parser

from .exceptions import XPathDateTimeException


def parse_datetime(dt_str):
    eastern_tz = pytz.timezone("America/New_York")
    try:
        dt = dateutil.parser.parse(dt_str)
    except ValueError:
        raise XPathDateTimeException("Could not parse datetime %s" % dt_str)
    else:
        if dt.tzinfo is None:
            return dt
        else:
            eastern_dt = eastern_tz.normalize(dt.astimezone(eastern_tz))
            iso_fmt = "%Y-%m-%dT%H:%M:%S"
            naive_dt = dateutil.parser.parse(eastern_dt.strftime(iso_fmt))
            return naive_dt
