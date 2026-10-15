from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer

from .repository import ProductRepository
from .schemas import Product
from .scraper import RetailScraper, RetailerConfig

app = typer.Typer(help="Scrape retailer listings and load them into the recommender database.")


@app.callback()
def main() -> None:
    """Retail-event ingestion commands."""


@app.command()
def scrape(config: Path = typer.Argument(..., exists=True), database: str = "data/retail.db") -> None:
    """Run a configured, rate-limited retail scrape."""
    settings = RetailerConfig.from_dict(json.loads(config.read_text(encoding="utf-8")))
    products = asyncio.run(RetailScraper(settings).scrape())
    ProductRepository(database).upsert_many(products)
    typer.echo(f"Stored {len(products)} products from {settings.name}.")


@app.command("seed-demo")
def seed_demo(database: str = "data/retail.db") -> None:
    """Load safe local sample products for an end-to-end API demonstration."""
    products = [
        Product(source="demo", external_id="wireless-headphones", title="Wireless Noise-Cancelling Headphones",
                url="https://example.invalid/products/headphones", category="electronics", brand="Demo Audio",
                current_price=89.99, original_price=149.99, rating=4.6, review_count=842, availability="InStock"),
        Product(source="demo", external_id="smartwatch", title="Fitness Smartwatch",
                url="https://example.invalid/products/smartwatch", category="electronics", brand="Demo Wear",
                current_price=119.99, original_price=199.99, rating=4.4, review_count=306, availability="InStock"),
        Product(source="demo", external_id="coffee-maker", title="Compact Coffee Maker",
                url="https://example.invalid/products/coffee-maker", category="home", brand="Demo Home",
                current_price=54.99, original_price=79.99, rating=4.2, review_count=91, availability="InStock"),
    ]
    ProductRepository(database).upsert_many(products)
    typer.echo(f"Stored {len(products)} local demo products in {database}.")


if __name__ == "__main__":
    app()
