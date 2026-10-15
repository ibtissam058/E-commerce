"""Respectful, configurable product-page and listing-page scraper.

Only scrape public pages you are entitled to access.  Robots rules, throttling,
timeouts and a descriptive user agent are enabled by default.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from .schemas import Product

LOG = logging.getLogger(__name__)
MONEY_RE = re.compile(r"(?:[A-Z]{3}\s*)?[$€£₺]?\s*([0-9][0-9.,]*)")


@dataclass(slots=True)
class RetailerConfig:
    name: str
    start_urls: list[str]
    product_selector: str = "[data-product-id]"
    selectors: dict[str, str] = field(default_factory=dict)
    allowed_domains: list[str] = field(default_factory=list)
    request_delay_seconds: float = 1.0
    max_pages: int = 10

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RetailerConfig":
        return cls(**data)


class RetailScraper:
    def __init__(self, config: RetailerConfig, *, user_agent: str = "RetailEventRecommender/1.0 (+contact@example.com)"):
        self.config = config
        self.user_agent = user_agent
        self._robots: dict[str, RobotFileParser] = {}

    async def scrape(self) -> list[Product]:
        """Fetch configured listing pages, deduplicate, and return normalized products."""
        products: dict[tuple[str, str], Product] = {}
        async with httpx.AsyncClient(headers={"User-Agent": self.user_agent}, follow_redirects=True, timeout=20) as client:
            for page_index, url in enumerate(self.config.start_urls[: self.config.max_pages]):
                if not await self._allowed(url, client):
                    LOG.warning("Skipped %s because robots.txt disallows it", url)
                    continue
                html = await self._fetch(client, url)
                if not html:
                    continue
                for product in self._extract_products(html, url):
                    products[(product.source, product.external_id)] = product
                if page_index + 1 < len(self.config.start_urls):
                    await asyncio.sleep(self.config.request_delay_seconds)
        return list(products.values())

    async def _allowed(self, url: str, client: httpx.AsyncClient) -> bool:
        parsed = urlparse(url)
        if self.config.allowed_domains and parsed.netloc not in self.config.allowed_domains:
            return False
        base = f"{parsed.scheme}://{parsed.netloc}"
        if base not in self._robots:
            parser = RobotFileParser()
            try:
                response = await client.get(f"{base}/robots.txt")
                if response.is_success:
                    parser.parse(response.text.splitlines())
                else:
                    parser.disallow_all = True
            except httpx.HTTPError:
                parser.disallow_all = True  # unavailable policy is not permission to scrape
            self._robots[base] = parser
        return self._robots[base].can_fetch(self.user_agent, url)

    async def _fetch(self, client: httpx.AsyncClient, url: str) -> str | None:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPError as exc:
            LOG.warning("Request failed for %s: %s", url, exc)
            return None

    def _extract_products(self, html: str, page_url: str) -> list[Product]:
        soup = BeautifulSoup(html, "html.parser")
        products = self._from_json_ld(soup, page_url)
        if products:
            return products
        return self._from_selectors(soup, page_url)

    def _from_json_ld(self, soup: BeautifulSoup, page_url: str) -> list[Product]:
        found: list[Product] = []
        for tag in soup.select('script[type="application/ld+json"]'):
            try:
                payload = json.loads(tag.get_text(strip=True))
            except json.JSONDecodeError:
                continue
            for item in self._walk_json(payload):
                kind = item.get("@type", "")
                if isinstance(kind, list):
                    kind = " ".join(kind)
                if "Product" not in str(kind):
                    continue
                product = self._to_product(item, page_url)
                if product:
                    found.append(product)
        return found

    def _walk_json(self, value: Any):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from self._walk_json(child)
        elif isinstance(value, list):
            for child in value:
                yield from self._walk_json(child)

    def _to_product(self, item: dict[str, Any], page_url: str) -> Product | None:
        offers = item.get("offers", {})
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        price = self._price(offers.get("price") or item.get("price"))
        title = item.get("name")
        if not title or price is None:
            return None
        url = urljoin(page_url, item.get("url") or page_url)
        external_id = str(item.get("sku") or item.get("productID") or self._stable_id(url, title))
        aggregate = item.get("aggregateRating") or {}
        image = item.get("image")
        return Product(source=self.config.name, external_id=external_id, title=title, url=url,
                       category=item.get("category") or "unknown", brand=self._name(item.get("brand")),
                       currency=offers.get("priceCurrency") or "USD", current_price=price,
                       original_price=self._price(item.get("highPrice") or offers.get("highPrice")),
                       rating=self._price(aggregate.get("ratingValue")),
                       review_count=self._integer(aggregate.get("reviewCount")),
                       image_url=image[0] if isinstance(image, list) and image else image,
                       availability=str(offers.get("availability") or "unknown"), raw=item)

    def _from_selectors(self, soup: BeautifulSoup, page_url: str) -> list[Product]:
        s = self.config.selectors
        required = ("title", "price")
        if not all(key in s for key in required):
            return []
        products = []
        for card in soup.select(self.config.product_selector):
            title = self._text(card, s["title"])
            price = self._price(self._text(card, s["price"]))
            if not title or price is None:
                continue
            url = urljoin(page_url, self._attribute(card, s.get("url", "a"), "href") or page_url)
            products.append(Product(source=self.config.name, external_id=self._stable_id(url, title), title=title,
                url=url, category=self._text(card, s.get("category", "")) or "unknown",
                currency=self._text(card, s.get("currency", "")) or "USD", current_price=price,
                original_price=self._price(self._text(card, s.get("original_price", ""))),
                rating=self._price(self._text(card, s.get("rating", ""))),
                image_url=urljoin(page_url, self._attribute(card, s.get("image", "img"), "src") or "")))
        return products

    @staticmethod
    def _text(node: Any, selector: str) -> str | None:
        if not selector:
            return None
        match = node.select_one(selector)
        return match.get_text(" ", strip=True) if match else None

    @staticmethod
    def _attribute(node: Any, selector: str, attribute: str) -> str | None:
        match = node.select_one(selector)
        return match.get(attribute) if match else None

    @staticmethod
    def _price(value: Any) -> float | None:
        if value is None:
            return None
        match = MONEY_RE.search(str(value).replace("\u00a0", " "))
        if not match:
            return None
        token = match.group(1)
        # Handles 1,299.99 and 1.299,99 with a conservative normalisation.
        if token.count(",") and token.count("."):
            token = token.replace(",", "") if token.rfind(".") > token.rfind(",") else token.replace(".", "").replace(",", ".")
        elif token.count(",") == 1 and len(token.rsplit(",", 1)[1]) == 2:
            token = token.replace(",", ".")
        else:
            token = token.replace(",", "")
        try:
            return float(Decimal(token))
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _name(value: Any) -> str | None:
        return value.get("name") if isinstance(value, dict) else str(value) if value else None

    @staticmethod
    def _integer(value: Any) -> int:
        match = re.search(r"\d+", str(value or ""))
        return int(match.group()) if match else 0

    @staticmethod
    def _stable_id(url: str, title: str) -> str:
        return hashlib.sha256(f"{url}|{title}".encode()).hexdigest()[:20]
