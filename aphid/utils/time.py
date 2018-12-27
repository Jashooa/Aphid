import datetime
import re

# import parsedatetime as pdt
# from dateutil.relativedelta import relativedelta
from discord.ext import commands


class ShortTime:
    compiled = re.compile("""(?:(?P<weeks>[0-9]{1,4})(?:weeks?|w))?                 # e.g. 10w
                             (?:(?P<days>[0-9]{1,5})(?:days?|d))?                   # e.g. 14d
                             (?:(?P<hours>[0-9]{1,5})(?:hours?|h))?                 # e.g. 12h
                             (?:(?P<minutes>[0-9]{1,5})(?:minutes?|m))?             # e.g. 10m
                             (?:(?P<seconds>[0-9]{1,5})(?:seconds?|s))?             # e.g. 15s
                             (?:(?P<milliseconds>[0-9]{1,4})(?:milliseconds?|ms))?  # e.g. 15ms
                          """, re.VERBOSE)

    def __init__(self, argument):
        match = self.compiled.fullmatch(argument)
        if match is None or not match.group(0):
            raise commands.BadArgument('Invalid time provided.')

        data = {k: int(v) for k, v in match.groupdict(default=0).items()}
        self.delta = datetime.timedelta(**data)
        self.datetime = datetime.datetime.utcnow() + self.delta


def human_timedelta(delta, precise=False, largest_only=False):
    delta_minutes = delta.seconds // 60
    delta_hours = delta.seconds // 3600
    delta_minutes -= delta_hours * 60
    # delta_weeks = delta.days // 7
    delta_seconds = delta.seconds - delta_minutes * 60 - delta_hours * 3600
    # delta_days = delta.days - delta_weeks * 7
    delta_days = delta.days
    delta_milliseconds = delta.microseconds // 1000
    delta_microseconds = delta.microseconds - delta_milliseconds * 1000

    values_and_names = [
        # (delta_weeks, 'week'),
        (delta_days, 'day'),
        (delta_hours, 'hour'),
        (delta_minutes, 'minute'),
        (delta_seconds, 'second')
    ]

    if precise:
        values_and_names.append((delta_milliseconds, 'millisecond'))
        values_and_names.append((delta_microseconds, 'microsecond'))

    text = ''
    for value, name in values_and_names:
        if value > 0:
            plural = 's' if value > 1 else ''
            if largest_only:
                return f'{value} {name}{plural}'

            text += ', ' if len(text) else ''
            text += f'{value} {name}'
            text += plural

    if text.find(',') > 0:
        text = ' and '.join(text.rsplit(', ', 1))

    return text


'''class ShortTimeRelative:
    compiled = re.compile("""(?:(?P<years>[0-9])(?:years?|y))?             # e.g. 2y
                             (?:(?P<months>[0-9]{1,2})(?:months?|mo))?     # e.g. 2months
                             (?:(?P<weeks>[0-9]{1,4})(?:weeks?|w))?        # e.g. 10w
                             (?:(?P<days>[0-9]{1,5})(?:days?|d))?          # e.g. 14d
                             (?:(?P<hours>[0-9]{1,5})(?:hours?|h))?        # e.g. 12h
                             (?:(?P<minutes>[0-9]{1,5})(?:minutes?|m))?    # e.g. 10m
                             (?:(?P<seconds>[0-9]{1,5})(?:seconds?|s))?    # e.g. 15s
                          """, re.VERBOSE)

    def __init__(self, argument):
        match = self.compiled.fullmatch(argument)
        if match is None or not match.group(0):
            raise commands.BadArgument('Invalid time provided.')

        data = {k: int(v) for k, v in match.groupdict(default=0).items()}
        now = datetime.datetime.utcnow()
        self.relative = relativedelta(**data)
        self.datetime = now + self.relative

    def to_human(self):
        delta = self.relative

        if delta.microseconds and delta.seconds:
            delta = delta + relativedelta(seconds=+1)

        attrs = ['years', 'months', 'days', 'hours', 'minutes', 'seconds']

        output = []
        for attr in attrs:
            elem = getattr(delta, attr)
            if not elem:
                continue

            if elem > 1:
                output.append(f'{elem} {attr}')
            else:
                output.append(f'{elem} {attr[:-1]}')

        if len(output) == 0:
            return 'now'
        elif len(output) == 1:
            return output[0]
        elif len(output) == 2:
            return f'{output[0]} and {output[1]}'
        else:
            return f'{output[0]}, {output[1]} and {output[2]}'



class HumanTime:
    calendar = pdt.Calendar(version=pdt.VERSION_CONTEXT_STYLE)

    def __init__(self, argument):
        now = datetime.datetime.utcnow()
        dt, status = self.calendar.parseDT(argument, sourceTime=now)
        if not status.hasDateOrTime:
            raise commands.BadArgument('Invalid time provided, try e.g. "tomorrow" or "3 days".')

        if not status.hasTime:
            # replace it with the current time
            dt = dt.replace(hour=now.hour, minute=now.minute, second=now.second, microsecond=now.microsecond)

        self.dt = dt
        self._past = dt < now


class Time(HumanTime):
    def __init__(self, argument):
        try:
            o = ShortTime(argument)
        except Exception:
            super().__init__(argument)
        else:
            self.dt = o.dt
            self._past = False


class FutureTime(Time):
    def __init__(self, argument):
        super().__init__(argument)

        if self._past:
            raise commands.BadArgument('This time is in the past.')


class UserFriendlyTime(commands.Converter):
    """That way quotes aren't absolutely necessary."""
    def __init__(self, converter=None, *, default=None):
        if isinstance(converter, type) and issubclass(converter, commands.Converter):
            converter = converter()

        if converter is not None and not isinstance(converter, commands.Converter):
            raise TypeError('commands.Converter subclass necessary.')

        self.converter = converter
        self.default = default

    async def check_constraints(self, ctx, now, remaining):
        if self.dt < now:
            raise commands.BadArgument('This time is in the past.')

        if not remaining:
            if self.default is None:
                raise commands.BadArgument('Missing argument after the time.')
            remaining = self.default

        if self.converter is not None:
            self.arg = await self.converter.convert(ctx, remaining)
        else:
            self.arg = remaining
        return self

    async def convert(self, ctx, argument):
        try:
            calendar = HumanTime.calendar
            regex = ShortTime.compiled
            now = datetime.datetime.utcnow()

            match = regex.match(argument)
            if match is not None and match.group(0):
                data = {k: int(v) for k, v in match.groupdict(default=0).items()}
                remaining = argument[match.end():].strip()
                self.dt = now + relativedelta(**data)
                return await self.check_constraints(ctx, now, remaining)

            # apparently nlp does not like 'from now'
            # it likes 'from x' in other cases though so let me handle the 'now' case
            if argument.endswith('from now'):
                argument = argument[:-8].strip()

            if argument[0:2] == 'me':
                # starts with 'me to' or 'me in'
                if argument[0:6] in ('me to ', 'me in '):
                    argument = argument[6:]

            elements = calendar.nlp(argument, sourceTime=now)
            if elements is None or len(elements) == 0:
                raise commands.BadArgument('Invalid time provided, try e.g. "tomorrow" or "3 days".')

            # handle the following cases:
            # 'date time' foo
            # date time foo
            # foo date time

            # first the first two cases:
            dt, status, begin, end, dt_string = elements[0]

            if not status.hasDateOrTime:
                raise commands.BadArgument('Invalid time provided, try e.g. "tomorrow" or "3 days".')

            if begin not in (0, 1) and end != len(argument):
                raise commands.BadArgument('Time is either in an inappropriate location, which '
                                           'must be either at the end or beginning of your input, '
                                           'or I just flat out did not understand what you meant. Sorry.')

            if not status.hasTime:
                # replace it with the current time
                dt = dt.replace(hour=now.hour, minute=now.minute, second=now.second, microsecond=now.microsecond)

            self.dt = dt

            if begin in (0, 1):
                if begin == 1:
                    # check if it's quoted:
                    if argument[0] != '"':
                        raise commands.BadArgument('Expected quote before time input...')

                    if not (end < len(argument) and argument[end] == '"'):
                        raise commands.BadArgument('If the time is quoted, you must unquote it.')

                    remaining = argument[end + 1:].lstrip(' ,.!')
                else:
                    remaining = argument[end:].lstrip(' ,.!')
            elif len(argument) == end:
                remaining = argument[:begin].strip()

            return await self.check_constraints(ctx, now, remaining)
        except Exception:
            import traceback
            traceback.print_exc()
            raise


def human_timedelta(dt, *, source=None):
    now = source or datetime.datetime.utcnow()
    if dt > now:
        delta = relativedelta(dt, now)
        suffix = ''
    else:
        delta = relativedelta(now, dt)
        suffix = ' ago'

    if delta.microseconds and delta.seconds:
        delta = delta + relativedelta(seconds=+1)

    attrs = ['years', 'months', 'days', 'hours', 'minutes', 'seconds']

    output = []
    for attr in attrs:
        elem = getattr(delta, attr)
        if not elem:
            continue

        if elem > 1:
            output.append(f'{elem} {attr}')
        else:
            output.append(f'{elem} {attr[:-1]}')

    if len(output) == 0:
        return 'now'
    elif len(output) == 1:
        return output[0] + suffix
    elif len(output) == 2:
        return f'{output[0]} and {output[1]}{suffix}'
    else:
        return f'{output[0]}, {output[1]} and {output[2]}{suffix}'

'''
