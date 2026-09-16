# Redline

Redline scores the risk of a contract clause by reconciling two independent
signals instead of trusting either one blindly:

1. **Semantic check** — embeds the input clause and finds its nearest
   neighbors in the [CUAD](https://www.atticusprojectai.org/cuad) dataset of
   real, expert-labeled contract clauses. This catches risk even when the
   wording is unusual.
2. **Heuristic check** — scans the clause against a curated list of known
   red-flag phrases and legal terms (e.g. "sole discretion", "uncapped
   liability", "perpetual", "without cause").

The two signals are combined into a single **risk score + confidence
score**. If they disagree, Redline says so explicitly instead of silently
picking a winner — that disagreement is itself useful information for the
caller.

Every request is logged to Postgres (JSONB) with full audit metadata, and
results are served through a REST API following a standardized envelope
(data / meta / freshness / provenance / trust / license / api / warnings)
designed for AI agent consumption.

## Architecture

```
                ┌─────────────────────┐
   clause  ───▶ │   FastAPI /v1/...    │
                └──────────┬───────────┘
                           │
             ┌─────────────┼──────────────┐
             ▼                            ▼
   ┌───────────────────┐        ┌───────────────────┐
   │  Semantic engine   │        │  Heuristic engine  │
   │  (embeddings +     │        │  (regex red-flag   │
   │   CUAD index)      │        │   rule set)        │
   └─────────┬──────────┘        └─────────┬──────────┘
             │                              │
             └──────────────┬───────────────┘
                             ▼
                   ┌───────────────────┐
                   │  Consensus engine  │
                   │  risk / confidence │
                   │  / agreement check │
                   └─────────┬──────────┘
                             ▼
                 ┌────────────────────────┐
                 │   Postgres (JSONB)      │
                 │  raw_clauses            │
                 │  consensus_results      │
                 │  audit_rollups          │
                 └────────────────────────┘
                             ▲
                    TTL purge / rollup job
                     (APScheduler, periodic)
```

## Setup

1. **Start Postgres**
   ```bash
   docker compose up -d
   ```

2. **Install dependencies**
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Get CUAD and build the semantic index** (one-time)
   ```bash
   python backend/scripts/download_cuad.py
   python backend/scripts/build_index.py
   ```

4. **Initialize the database schema**
   ```bash
   psql "$DATABASE_URL" -f backend/migrations/001_init.sql
   ```

5. **Run the API**
   ```bash
   uvicorn backend.app.main:app --reload
   ```

6. **Try the demo frontend**
   Open `frontend/index.html` in a browser (or serve it with any static
   server) and paste a contract clause.

## Testing

```bash
pytest backend/tests -v
```

Covers: API availability, p95 latency, freshness SLA enforcement, consensus
correctness against known CUAD-labeled clauses, and failover behavior when
one engine fails.

## Key terms

Semantic similarity search · sentence embeddings · vector/nearest-neighbor
retrieval · CUAD · rule-based classification · multi-signal consensus ·
confidence calibration · legal NLP · PostgreSQL JSONB · data lineage &
provenance · graceful degradation · SLA/latency testing.
