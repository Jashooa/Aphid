# Stolen from https://github.com/slice/lifesaver/blob/master/lifesaver/utils/formatting.py


def escape_backticks(text: str) -> str:
    """
    Replace backticks with a homoglyph to prevent codeblock and inline code breakout.
    Parameters
    ----------
    text : str
        The text to escape.
    Returns
    -------
    str
        The escaped text.
    """
    return text.replace('\N{GRAVE ACCENT}', '\N{MODIFIER LETTER GRAVE ACCENT}')


def codeblock(code: str, *, lang: str = '', escape: bool = True) -> str:
    """
    Construct a Markdown codeblock.
    Parameters
    ----------
    code
        The code to insert into the codeblock.
    lang
        The string to mark as the language when formatting.
    escape
        Prevents the code from escaping from the codeblock.
    Returns
    -------
    str
        The formatted codeblock.
    """
    return '```{}\n{}\n```'.format(
        lang,
        escape_backticks(code) if escape else code,
    )


def cleanup_code(code: str) -> str:
    """
    Automatically removes code blocks from the code.
    Parameters
    ----------
    code
        The code to clean.
    Returns
    -------
    str
        The cleaned code.
    """
    # remove ```py\n```
    if code.startswith('```') and code.endswith('```'):
        return '\n'.join(code.split('\n')[1:-1])

    # remove `foo`
    return code.strip('` \n')


def truncate(text: str, desired_length: int, *, suffix: str = '…') -> str:
    """
    Truncates text and returns it. Three periods will be inserted as a suffix.
    Parameters
    ----------
    text
        The text to truncate.
    desired_length
        The desired length.
    suffix
        The text to insert before the desired length is reached.
        By default, this is '...' to indicate truncation.
    """
    if len(text) > desired_length:
        return text[:desired_length - len(suffix)] + suffix
    else:
        return text


def pluralise(*, with_quantity: bool = True, with_indicative: bool = False, **word) -> str:
    """
    Pluralise a single kwarg's name depending on the value.
    Example
    -------
    >>> pluralise(object=2)
    "objects"
    >>> pluralise(object=1)
    "object"
    """

    try:
        items = word.items()
        kwargs = {'with_quantity', 'with_indicative'}
        key = next(item[0] for item in items if item not in kwargs)
    except KeyError:
        raise ValueError('Cannot find kwarg key to pluralise')

    value = word[key]

    with_s = key + ('' if value == 1 else 's')
    indicative = ''

    if with_indicative:
        indicative = ' is' if value == 1 else ' are'

    if with_quantity:
        return f'{value} {with_s}{indicative}'
    else:
        return with_s + indicative


def human_join(seq, delim=', ', final='or'):
    size = len(seq)
    if size == 0:
        return ''

    if size == 1:
        return seq[0]

    if size == 2:
        return f'{seq[0]} {final} {seq[1]}'

    return delim.join(seq[:-1]) + f' {final} {seq[-1]}'


class TabularData:
    def __init__(self):
        self._widths = []
        self._columns = []
        self._rows = []

    def set_columns(self, columns):
        self._columns = columns
        self._widths = [len(c) + 2 for c in columns]

    def add_row(self, row):
        rows = [str(r) for r in row]
        self._rows.append(rows)
        for index, element in enumerate(rows):
            width = len(element) + 2
            if width > self._widths[index]:
                self._widths[index] = width

    def add_rows(self, rows):
        for row in rows:
            self.add_row(row)

    def render(self):
        """Renders a table in rST format.

        Example:

        +-------+-----+
        | Name  | Age |
        +-------+-----+
        | Alice | 24  |
        |  Bob  | 19  |
        +-------+-----+
        """

        sep = '+'.join('-' * w for w in self._widths)
        sep = f'+{sep}+'

        to_draw = [sep]

        def get_entry(d):
            elem = '|'.join(f'{e:^{self._widths[i]}}' for i, e in enumerate(d))
            return f'|{elem}|'

        to_draw.append(get_entry(self._columns))
        to_draw.append(sep)

        for row in self._rows:
            to_draw.append(get_entry(row))

        to_draw.append(sep)
        return '\n'.join(to_draw)
