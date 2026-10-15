from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from .recommender import EventAwareRanker
from .repository import ProductRepository
from .schemas import EventContext, Recommendation

app = FastAPI(title="Retail Event Recommender", version="1.0.0")
repository = ProductRepository()
ranker = EventAwareRanker()
STATIC_DIR = Path(__file__).parent / "static"


@app.get("/", include_in_schema=False)
def interface() -> FileResponse:
    """Serve the browser-based recommendation interface."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model_version": ranker.model_version}


@app.post("/recommendations", response_model=list[Recommendation])
def recommendations(context: EventContext, limit: int = Query(default=10, ge=1, le=50)) -> list[Recommendation]:
    products = repository.list_products(context.category)
    if not products:
        raise HTTPException(404, "No matching products available. Run the scraper first.")
    return ranker.recommend(products, context, limit)
