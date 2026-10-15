from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .schemas import Product


class ProductRepository:
    def __init__(self, database_path: str = "data/retail.db"):
        self.path = Path(database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS products (
                source TEXT NOT NULL, external_id TEXT NOT NULL, payload TEXT NOT NULL,
                updated_at TEXT NOT NULL, PRIMARY KEY (source, external_id))""")

    def upsert_many(self, products: list[Product]) -> int:
        with self._connect() as db:
            db.executemany("""INSERT INTO products(source, external_id, payload, updated_at) VALUES (?, ?, ?, ?)
                ON CONFLICT(source, external_id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at""",
                [(p.source, p.external_id, p.model_dump_json(), p.scraped_at.isoformat()) for p in products])
        return len(products)

    def list_products(self, category: str | None = None) -> list[Product]:
        query = "SELECT payload FROM products"
        params: tuple[str, ...] = ()
        if category:
            query += " WHERE lower(json_extract(payload, '$.category')) = lower(?)"
            params = (category,)
        with self._connect() as db:
            return [Product.model_validate_json(row["payload"]) for row in db.execute(query, params)]
