
# https://docs.djangoproject.com/en/1.9/_modules/django/utils/dateparse
# https://bitbucket.org/micktwomey/pyiso8601/src/f72a24982d914a02ad09e2452fc7fc66c08d27d5/iso8601/iso8601.py?at=default&fileviewer=file-view-default

# https://en.wikipedia.org/wiki/ISO_8601

import re, datetime

datetime_re = re.compile(
    r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})'
    r'(?:[T ](?P<hour>\d{1,2}):(?P<minute>\d{1,2})'
    r'(?::(?P<second>\d{1,2})(?:\.(?P<microsecond>\d{1,6})\d{0,6})?)?'
    r'(?P<tzinfo>Z|[+-]\d{2}(?::?\d{2})?)?)?$'
)


iso8601_duration_re = re.compile(
    r'^P'
    r'(?:(?P<days>\d+(.\d+)?)D)?'
    r'(?:T'
    r'(?:(?P<hours>\d+(.\d+)?)H)?'
    r'(?:(?P<minutes>\d+(.\d+)?)M)?'
    r'(?:(?P<seconds>\d+(.\d+)?)S)?'
    r')?'
    r'$'
)

# ISO8601_REGEX = re.compile(
#     r"""
#     (?P<year>[0-9]{4})
#     (
#         (
#             (-(?P<monthdash>[0-9]{1,2}))
#             |
#             (?P<month>[0-9]{2})
#             (?!$)  # Don't allow YYYYMM
#         )
#         (
#             (
#                 (-(?P<daydash>[0-9]{1,2}))
#                 |
#                 (?P<day>[0-9]{2})
#             )
#             (
#                 (
#                     (?P<separator>[ T])
#                     (?P<hour>[0-9]{2})
#                     (:{0,1}(?P<minute>[0-9]{2})){0,1}
#                     (
#                         :{0,1}(?P<second>[0-9]{1,2})
#                         ([.,](?P<second_fraction>[0-9]+)){0,1}
#                     ){0,1}
#                     (?P<timezone>
#                         Z
#                         |
#                         (
#                             (?P<tz_sign>[-+])
#                             (?P<tz_hour>[0-9]{2})
#                             :{0,1}
#                             (?P<tz_minute>[0-9]{2}){0,1}
#                         )
#                     ){0,1}
#                 ){0,1}
#             )
#         ){0,1}  # YYYY-MM
#     ){0,1}  # YYYY only
#     $
#     """,
#     re.VERBOSE
# )


def parse_datetime(value):
    """Parses a string and return a datetime.datetime.

    This function supports time zone offsets. When the input contains one,
    the output uses a timezone with a fixed offset from UTC.

    Raises ValueError if the input is well formatted but not a valid datetime.
    Returns None if the input isn't well formatted.
    """
    match = datetime_re.match(value)
    if match:
        kw = match.groupdict()
        if kw['microsecond']:
            kw['microsecond'] = kw['microsecond'].ljust(6, '0')
        tzinfo = kw.pop('tzinfo')
        if tzinfo == 'Z':
            tzinfo = utc
        elif tzinfo is not None:
            offset_mins = int(tzinfo[-2:]) if len(tzinfo) > 3 else 0
            offset = 60 * int(tzinfo[1:3]) + offset_mins
            if tzinfo[0] == '-':
                offset = -offset
            tzinfo = get_fixed_timezone(offset)
        kw = {k: int(v) for k, v in kw.items() if v is not None}
        kw['tzinfo'] = tzinfo
        return datetime.datetime(**kw)

print(parse_datetime('2017-8-7'))
