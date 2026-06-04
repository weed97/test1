"""In-world time: a clock, a calendar, seasons and a day/night cycle.

Aetheria runs on its own calendar.  One *day* is divided into 24 hours; the
simulation advances in *ticks* (one tick == one in-world hour by default).  A
year has four seasons of 30 days each (120 days total).  Months map onto a small
fantasy calendar so flavour text can reference named months and weekdays.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

HOURS_PER_DAY = 24
DAYS_PER_SEASON = 30
SEASONS_PER_YEAR = 4
DAYS_PER_YEAR = DAYS_PER_SEASON * SEASONS_PER_YEAR


class Season(str, Enum):
    SPRING = "Spring"
    SUMMER = "Summer"
    AUTUMN = "Autumn"
    WINTER = "Winter"

    @property
    def flavour(self) -> str:
        return {
            Season.SPRING: "Green shoots break through the thawing earth.",
            Season.SUMMER: "The sun hangs long and heavy over the realm.",
            Season.AUTUMN: "Leaves turn amber and the harvest is gathered.",
            Season.WINTER: "Frost grips the land and the nights grow long.",
        }[self]


MONTH_NAMES = [
    "Frostwane", "Seedfall", "Bloomtide",      # spring
    "Highsun", "Emberlight", "Goldreap",        # summer
    "Mistral", "Duskfall", "Harvestmoon",       # autumn
    "Hollowdark", "Snowbind", "Yulemark",       # winter
]
WEEKDAY_NAMES = ["Sunday", "Moonday", "Forgeday", "Wyrmsday",
                 "Hearthday", "Veilday", "Starday"]


class TimeOfDay(str, Enum):
    DAWN = "Dawn"
    MORNING = "Morning"
    NOON = "Noon"
    AFTERNOON = "Afternoon"
    DUSK = "Dusk"
    NIGHT = "Night"
    MIDNIGHT = "Midnight"

    @property
    def is_dark(self) -> bool:
        return self in (TimeOfDay.DUSK, TimeOfDay.NIGHT, TimeOfDay.MIDNIGHT)


@dataclass
class GameClock:
    """Tracks the passage of in-world time, measured in elapsed hours."""

    total_hours: int = 6  # start the world at dawn of day 1

    # -- derived read-only views --------------------------------------------
    @property
    def hour(self) -> int:
        return self.total_hours % HOURS_PER_DAY

    @property
    def day_index(self) -> int:
        """Zero-based day number since the world began."""
        return self.total_hours // HOURS_PER_DAY

    @property
    def day_of_year(self) -> int:
        return self.day_index % DAYS_PER_YEAR

    @property
    def year(self) -> int:
        return self.day_index // DAYS_PER_YEAR + 1

    @property
    def season(self) -> Season:
        season_index = (self.day_of_year // DAYS_PER_SEASON) % SEASONS_PER_YEAR
        return list(Season)[season_index]

    @property
    def day_of_season(self) -> int:
        return self.day_of_year % DAYS_PER_SEASON + 1

    @property
    def month_name(self) -> str:
        month_index = (self.day_of_year // 10) % len(MONTH_NAMES)
        return MONTH_NAMES[month_index]

    @property
    def weekday(self) -> str:
        return WEEKDAY_NAMES[self.day_index % len(WEEKDAY_NAMES)]

    @property
    def time_of_day(self) -> TimeOfDay:
        h = self.hour
        if 5 <= h < 7:
            return TimeOfDay.DAWN
        if 7 <= h < 11:
            return TimeOfDay.MORNING
        if 11 <= h < 13:
            return TimeOfDay.NOON
        if 13 <= h < 17:
            return TimeOfDay.AFTERNOON
        if 17 <= h < 20:
            return TimeOfDay.DUSK
        if 20 <= h < 24:
            return TimeOfDay.NIGHT
        return TimeOfDay.MIDNIGHT

    @property
    def is_night(self) -> bool:
        return self.time_of_day.is_dark

    # -- mutation ------------------------------------------------------------
    def advance(self, hours: int = 1) -> int:
        """Advance the clock and return the new ``total_hours``."""
        self.total_hours += max(0, hours)
        return self.total_hours

    # -- formatting ----------------------------------------------------------
    def clock_string(self) -> str:
        h = self.hour
        suffix = "am" if h < 12 else "pm"
        display = h % 12
        if display == 0:
            display = 12
        return f"{display:02d}:00 {suffix}"

    def stamp(self) -> str:
        return (f"Day {self.day_of_season} of {self.month_name}, Year {self.year} "
                f"({self.weekday}) — {self.time_of_day.value}, {self.clock_string()}")

    def short(self) -> str:
        return f"Y{self.year} D{self.day_index} {self.clock_string()}"

    def to_dict(self) -> dict:
        return {"total_hours": self.total_hours}

    @classmethod
    def from_dict(cls, data: dict) -> "GameClock":
        return cls(total_hours=int(data.get("total_hours", 6)))
