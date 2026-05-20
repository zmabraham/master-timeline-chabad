"""Pydantic models for EventRecord and nested types."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _StrictModel(BaseModel):
    """Every domain model rejects unknown fields — typos must fail loudly in a multi-pass pipeline."""
    model_config = ConfigDict(extra="forbid")

EventCategory = Literal[
    "rebbe",
    "publication",
    "conflict",
    "education",
    "organization",
    "location",
    "calendar",
    "general",
]
RebbeId = Literal[
    "besht",
    "magid",
    "alter",
    "mitteler",
    "tzemach-tzedek",
    "maharash",
    "rashab",
    "rayatz",
    "rebbe",
]
DatePrecision = Literal["year", "month", "day"]


class EventDate(_StrictModel):
    y: int = Field(ge=1500, le=2100)
    m: int | None = Field(default=None, ge=1, le=12)
    d: int | None = Field(default=None, ge=1, le=31)
    precision: DatePrecision

    @model_validator(mode="after")
    def _check_precision(self) -> Self:
        if self.precision == "day" and (self.m is None or self.d is None):
            raise ValueError("precision=day requires m and d")
        if self.precision == "month" and self.m is None:
            raise ValueError("precision=month requires m")
        if self.precision == "year" and (self.m is not None or self.d is not None):
            raise ValueError("precision=year must not have m or d")
        if self.precision == "month" and self.d is not None:
            raise ValueError("precision=month must not have d")
        return self


class HebrewDate(_StrictModel):
    y: int
    m: str | None = None
    d: int | None = None


class EventPhoto(_StrictModel):
    url: str
    credit: str
    caption: str | None = None


class EventSource(_StrictModel):
    name: str
    url: str | None = None
    page: int | None = None


class EventRecord(_StrictModel):
    """An event in the timeline.

    Intermediate-stage contract: ``title_en`` and ``summary_en`` MAY be empty
    strings in Pass 1 / Pass 2 outputs — Pass 3 fills English for any Hebrew-only
    record. Pass 5's emit-time linter is the authoritative gate that enforces
    non-empty title/summary on the final ``events.json``. ``id`` and ``story_path``
    are identity/location fields and must be non-empty at every stage.
    """

    id: str = Field(min_length=1)
    significance: int = Field(ge=0, le=100)
    date: EventDate
    hebrew_date: HebrewDate | None = None
    title_en: str                          # may be "" during Pass 1/2; filled by Pass 3
    summary_en: str                        # may be "" if a source row has no description
    story_body: str | None = None          # 2-4 sentence full story; written to stories/<id>.md by Pass 5
    story_path: str = Field(min_length=1)
    categories: list[EventCategory] = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    rebbe: RebbeId | None = None
    era: str | None = None
    photo: EventPhoto | None = None
    sources: list[EventSource]
    related: list[str] = Field(default_factory=list)
