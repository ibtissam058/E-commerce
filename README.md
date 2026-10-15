# Retail Event Promotion Recommender

An event-aware recommendation service for high-traffic retail periods such as Black Friday, Christmas, flash campaigns, and seasonal sales. It collects public product offers, normalizes prices and discounts, stores current inventory snapshots, and returns ranked promotions with human-readable reasons.

The scraper is deliberately a core module rather than a one-off script: each retailer gets a small JSON configuration, requests are throttled, public `robots.txt` rules are checked, errors are isolated per page, structured JSON-LD is preferred, and CSS selectors are available for sites that do not expose product JSON-LD.

## What is included

| Area | Implementation |
| --- | --- |
| Ingestion | Async `httpx` + Beautiful Soup scraper with robots checks, domain allow-list, deduplication, structured-data extraction, selector fallback, price normalization, and per-retailer configs |
| Data store | SQLite product snapshot repository with idempotent upserts |
| Online recommendations | FastAPI endpoint with event, urgency, category, and budget context; explainable low-latency ranking |
| Deep learning | PyTorch two-tower model and an offline CSV trainer exporting TorchScript |
| Quality | Typed Pydantic contracts and a ranking test |

## Architecture

```text
Retailer listing pages
        |
        v
Configured, rate-limited scraper -----> Product normalizer/deduplicator
        |                                         |
        |                                         v
        +-- robots.txt + allow-list          SQLite snapshots
                                                   |
Event context + user/session features             v
        |                                  Candidate retrieval
        +---------------------------->    + event-aware ranker
                                                   |
                                                   v
                                        FastAPI recommendations
```

### Why these choices

- **JSON-LD first, CSS fallback:** JSON-LD changes less often than a storefront's visual markup. The selector fallback makes retailer-specific integration practical without modifying Python code.
- **Async scraping with respectful controls:** Event pages are volatile and peak traffic is high. Async I/O keeps refresh jobs efficient; request delays, robots checks, timeouts, and a domain allow-list keep integrations bounded. Obtain a retailer's permission and respect its terms before scheduling a scraper.
- **SQLite snapshots:** dependable local development and simple upserts. In production, replace this adapter with Postgres and add a timestamped price-history table.
- **Two-stage serving:** the current explainable ranker ensures a useful system before interaction history exists. The model architecture is a two-tower neural ranker: user/event features and product features become 32-dimensional embeddings, whose dot product predicts engagement. Once trained, its TorchScript artifact is ready to serve behind the same candidate pipeline.
- **Real-time event signals:** `EventContext` carries event type, urgency, days remaining, category, and budget. The ranker raises the importance of discounts and urgency during Black Friday/flash events; a production feature store should additionally provide inventory, price velocity, impressions, clicks, cart additions, and purchases.

## Repository layout

```text
Python DL/
  retail_recommender/
    scraper.py       # scraper and retailer integration contract
    repository.py    # SQLite adapter
    recommender.py   # explainable online ranker
    model.py          # PyTorch two-tower model
    training.py       # offline CSV -> TorchScript trainer
    api.py            # FastAPI service
  configs/demo_retailer.json
  tests/test_recommender.py
  requirements.txt
  requirements-ml.txt
```

## Run it

From PowerShell:

```powershell
cd PythonDL
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scraper.py scrape configs/demo_retailer.json
uvicorn app:app --reload
```

For a local end-to-end demonstration before connecting an authorized retailer,
load the included sample catalog instead:

```powershell
python scraper.py seed-demo
```

Use `configs/demo_retailer.json` as a template: replace `example.com`, start URLs, allowed domains, and selectors with a retailer you have permission to scrape. The scraper attempts JSON-LD automatically, so selectors are only needed when structured product data is absent.

Retrieve recommendations after an ingestion run:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/recommendations `
  -ContentType 'application/json' `
  -Body '{"event":"black_friday","urgency":0.9,"budget":150,"category":"electronics"}'
```

The service documents its API at `http://127.0.0.1:8000/docs`.

## Train the neural model

Install the optional ML dependency and provide a CSV with eight `user_feature_0..7` columns, ten `item_feature_0..9` columns, and a binary `label` outcome.

```powershell
pip install -r requirements-ml.txt
python -m retail_recommender.training train data/demo_interactions.csv --output artifacts/two_tower.pt
```

Suggested features include category affinity, brand affinity, budget distance, event embedding, urgency, stock status, discount percentage, price percentile, rating, review volume, and price-change velocity. Train with chronological splits, generate negatives only from products displayed to the user, track NDCG@K/Recall@K and conversion lift, and retrain after each major event.

## Production checklist

- Put scrape jobs in a scheduler/queue (Celery, RQ, or cloud scheduler); use one configuration and rate limit per retailer.
- Use retailer APIs or written approval where available; do not bypass CAPTCHAs, authentication, rate limits, robots restrictions, or paywalls.
- Move product and interaction data to Postgres/object storage; keep a price history and data-retention policy.
- Cache recommendations, monitor scrape success/freshness, validate currency and outlier prices, and provide fallback rankings when model confidence is low.
- Keep PII out of training logs, use consented behavioral data, and audit recommendations for price and category bias.

## Test

```powershell
cd "Python DL"
python -m pytest
```
