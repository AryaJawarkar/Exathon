# Architecture

```
            RAW, FRAGMENTED FEEDS                UNIFIED IN EXASOL              DECISIONS
 ┌─────────────────────────────────┐      ┌──────────────────────────┐   ┌──────────────────┐
 │ online_orders.csv   (W-refs)     │      │  DIM_CUSTOMER            │   │  Demand Forecast │
 │ store_receipts.csv  (dd-mm-yyyy) │ ETL  │  DIM_PRODUCT            │   │  Customer Segments│
 │ marketplace_settlements.csv (fee)│ ───▶ │  FACT_SALES  ◀─ grain:  │──▶│  Churn & CLV     │
 │  ·different columns              │      │   one line item,        │   │  (Streamlit)     │
 │  ·different date formats         │      │   channel-tagged        │   └──────────────────┘
 │  ·gross vs net revenue           │      └──────────────────────────┘
 └─────────────────────────────────┘        all analytics = SQL here
```

## Why this shape wins on the rubric

- **Effective use of Exasol (25%)** — the warehouse is the product, not a bolt-on.
  RFM scoring (NTILE window functions), churn feature engineering, and all demand
  aggregation run *in* Exasol. Python only orchestrates and renders.
- **Innovation & impact (25%)** — directly targets *sales fragmentation*: three
  real-world-shaped feeds reconciled into one conformed star schema, then three
  decisions (what to stock, who to grow, who to keep) off that single source.
- **Reproducibility (10%)** — `docker compose up`, four commands, deterministic
  synthetic data (seeded). No proprietary data.

## Components

| Layer | Path | Role |
|------|------|------|
| Config | `src/config.py` | env-driven settings |
| DB | `src/db.py` | pyexasol connection + `query_df` |
| Schema | `src/sql/schema.sql` | conformed star schema |
| Synthetic data | `src/data/generate_synthetic_data.py` | fragmented feeds |
| ETL | `src/etl/load.py` | normalise + unify into `FACT_SALES` |
| Analytics | `src/analytics/{segmentation,forecasting,churn}.py` | the three modules |
| UI | `app/Home.py`, `app/pages/*` | Streamlit dashboard |

## Data model

`FACT_SALES` grain = one order line, tagged with `CHANNEL ∈ {ONLINE, STORE, MARKETPLACE}`,
joined to `DIM_CUSTOMER` and `DIM_PRODUCT`. Every downstream question is a single
query against this fact table.

## Modelling notes

- **Forecasting** — Ridge regression on `[trend, one-hot(day-of-week), one-hot(month)]`,
  per series, with a 95% residual band. Explainable and dependency-light.
- **Segmentation** — classic RFM, quintiles via `NTILE(5)`, mapped to named segments.
- **Churn** — label = no purchase in 90 days; `HistGradientBoostingClassifier` with
  out-of-fold probabilities (no leakage). CLV = monthly margin × 12 × retention odds;
  priority = churn risk × CLV.
