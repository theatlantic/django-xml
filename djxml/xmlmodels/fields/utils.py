from __future__ import absolute_import
import dateutil.parser

from ..exceptions import XPathDateTimeException


def parse_datetime(dt_str):
    try:
        return dateutil.parser.parse(dt_str)
    except ValueError:
        raise XPathDateTimeException("Could not parse datetime %s" % dt_str)
