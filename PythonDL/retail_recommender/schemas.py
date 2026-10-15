from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator


class RetailEvent(str, Enum):
    BLACK_FRIDAY = "black_friday"
    CHRISTMAS = "christmas"
    SEASONAL_SALE = "seasonal_sale"
    FLASH_SALE = "flash_sale"
    GENERIC = "generic"


class Product(BaseModel):
    source: str
    external_id: str
    title: str
    url: str
    category: str = "unknown"
    brand: str | None = None
    currency: str = "USD"
    current_price: float = Field(gt=0)
    original_price: float | None = Field(default=None, gt=0)
    rating: float | None = Field(default=None, ge=0, le=5)
    review_count: int = Field(default=0, ge=0)
    image_url: str | None = None
    availability: str = "unknown"
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True)
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def discount_pct(self) -> float:
        if not self.original_price or self.original_price <= self.current_price:
            return 0.0
        return round((1 - self.current_price / self.original_price) * 100, 2)

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("product title is required")
        return value


class EventContext(BaseModel):
    event: RetailEvent = RetailEvent.GENERIC
    urgency: float = Field(default=0.5, ge=0, le=1)
    days_until_end: float = Field(default=7, ge=0)
    category: str | None = None
    budget: float | None = Field(default=None, gt=0)


class Recommendation(BaseModel):
    product: Product
    score: float
    reasons: list[str]
    model_version: str
