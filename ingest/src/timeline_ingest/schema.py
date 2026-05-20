"""Pydantic models for EventRecord and nested types."""

from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

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


class EventDate(BaseModel):
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
        return self


class HebrewDate(BaseModel):
    y: int
    m: str | None = None
    d: int | None = None


class EventPhoto(BaseModel):
    url: str
    credit: str
    caption: str | None = None


class EventSource(BaseModel):
    name: str
    url: str | None = None
    page: int | None = None


class EventRecord(BaseModel):
    id: str
    significance: int = Field(ge=0, le=100)
    date: EventDate
    hebrew_date: HebrewDate | None = None
    title_en: str
    summary_en: str
    story_body: str | None = None         # 2-4 sentence full story; written to stories/<id>.md by Pass 5
    story_path: str
    categories: list[EventCategory] = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    rebbe: RebbeId | None = None
    era: str | None = None
    photo: EventPhoto | None = None
    sources: list[EventSource]
    related: list[str] = Field(default_factory=list)
