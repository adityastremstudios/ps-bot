import os
from typing import Any, Iterable

import discord

from .emojis import CROSS


async def send_simple_embed(channel: discord.TextChannel, description: str, delete_after: float = None) -> discord.Message:
    return await channel.send(
        embed=discord.Embed(color=int(os.getenv("DEFAULT_COLOR")), description=description), delete_after=delete_after
    )


async def send_error_embed(
    channel: discord.TextChannel, description: str, delete_after: float = None, image_url: str = None
) -> discord.Message:
    return await channel.send(
        embed=discord.Embed(color=discord.Color.red(), description=CROSS + " | " + description).set_image(url=image_url),
        delete_after=delete_after,
    )


def truncate_string(value: str, max_length=128, suffix="...") -> str:
    """
    Truncate a string to a certain length and add a suffix if it exceeds the length.
    """
    string_value = str(value)
    string_truncated = string_value[: min(len(string_value), (max_length - len(suffix)))]
    suffix = suffix if len(string_value) > max_length else ""
    return string_truncated + suffix


class plural:
    def __init__(self, value: int | list):
        self.value = value

        if isinstance(self.value, list):
            self.value = len(self.value)

    def __format__(self, format_spec: str):
        v = self.value
        singular, sep, plural = format_spec.partition("|")

        plural = plural or f"{singular}s"
        if abs(v) != 1:
            return f"{v} {plural}"
        return f"{v} {singular}"


class TabularData:
    def __init__(self):
        self._widths: list[int] = []
        self._columns: list[str] = []
        self._rows: list[list[str]] = []

    def set_columns(self, columns: list[str]):
        self._columns = columns
        self._widths = [len(c) + 2 for c in columns]

    def add_row(self, row: Iterable[Any]) -> None:
        rows = [str(r) for r in row]
        self._rows.append(rows)
        for index, element in enumerate(rows):
            width = len(element) + 2
            if width > self._widths[index]:
                self._widths[index] = width

    def add_rows(self, rows: Iterable[Iterable[Any]]) -> None:
        for row in rows:
            self.add_row(row)

    def render(self) -> str:
        """Renders a table in rST format.

        Example:

        +-------+-----+
        | Name  | Age |
        +-------+-----+
        | Alice | 24  |
        |  Bob  | 19  |
        +-------+-----+
        """

        sep = "+".join("-" * w for w in self._widths)
        sep = f"+{sep}+"

        to_draw = [sep]

        def get_entry(d):
            elem = "|".join(f"{e:^{self._widths[i]}}" for i, e in enumerate(d))
            return f"|{elem}|"

        to_draw.append(get_entry(self._columns))
        to_draw.append(sep)

        for row in self._rows:
            to_draw.append(get_entry(row))

        to_draw.append(sep)
        return "\n".join(to_draw)
