"""Create time-safe feature rows for offline two-tower training.

This module keeps feature construction outside the API so training and serving
can share the same definitions as the project grows.
"""
from __future__ import annotations

from retail_recommender.schemas import EventContext, Product


def product_features(product: Product) -> list[float]:
    """Ten normalized numerical product features for the item tower."""
    return [
        min(product.current_price / 1000, 1.0),
        min(product.discount_pct / 100, 1.0),
        min((product.rating or 0) / 5, 1.0),
        min(product.review_count / 1000, 1.0),
        1.0 if "instock" in product.availability.lower().replace(" ", "") else 0.0,
        1.0 if product.brand else 0.0,
        1.0 if product.image_url else 0.0,
        min(len(product.title) / 150, 1.0),
        min(len(product.category) / 40, 1.0),
        1.0,  # reserved for price-velocity from the history table
    ]


def event_features(context: EventContext, affinity: float = 0.0) -> list[float]:
    """Eight event/session features for the user-event tower."""
    event_index = list(type(context.event)).index(context.event) / max(len(type(context.event)) - 1, 1)
    return [event_index, context.urgency, min(context.days_until_end / 30, 1.0), affinity,
            min((context.budget or 0) / 1000, 1.0), float(context.category is not None), 0.0, 0.0]
