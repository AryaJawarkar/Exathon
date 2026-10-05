# 🛍️ Omnichannel Customer & Demand Intelligence

**ExaThon India 2026 — Track: *Customers, Channels & Demand***

A single unified Exasol warehouse that fixes **sales fragmentation** — then turns
it into three decisions every retailer needs:

| Module | Question it answers |
|--------|---------------------|
| 📈 **Demand Forecast** | How much of what, in which channel, over the next 30 days? |
| 👥 **Customer Segments** | Who are my Champions, and who's quietly slipping away? |
| ⚠️ **Churn & CLV** | Which *high-value* customers are about to leave — and are worth saving? |

> The retailer's data arrives as **three fragmented feeds** (online store, physical
> POS, marketplace) with different columns, date formats and revenue conventions.
> We reconcile them into one conformed star schema in **Exasol Personal**, and every
> analytics module is then a single query against that one source of truth.

---

## Why this fits the track & rubric

- **Sales fragmentation is the headline problem** of the *Customers, Channels &
  Demand* track — we tackle it head-on, not as a side effect.
- **Exasol is the engine, not a bolt-on** (25% of the score): RFM scoring uses
  `NTILE` window functions, churn features are a single in-DB `GROUP BY`, and all
  demand aggregation runs in Exasol. Python only orchestrates and renders.
- **Reproducible in minutes** with Docker + seeded synthetic data. No proprietary
  data (contest rule), MIT-licensed.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design.

---

## Quickstart

Prerequisites: Docker, Python 3.10+.

```bash
# 1. Start Exasol Personal locally (first boot ~2-3 min)
docker compose up -d

# 2. Python environment
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # defaults match the docker container

# 3. Build the data: generate fragmented feeds, then unify them in Exasol
python -m src.data.generate_synthetic_data
python -m src.etl.load

# 4. Launch the dashboard
streamlit run app/Home.py
```

Then open http://localhost:8501.

Prefer `make`? → `make db && make setup && make pipeline && make app`.

### Running against Exasol Personal on AWS/Azure

Skip `docker compose`. Point `.env` at your instance:

```
EXA_DSN=your-host:8563
EXA_USER=...
EXA_PASSWORD=...
```

---

## Verify it works (no database needed)

```bash
make smoke          # or: python -m tests.smoke
```

This checks synthetic-data generation, the channel-unification logic, and the
forecasting model offline.

---

## Project layout

```
.
├── docker-compose.yml          # Exasol Personal (local dev)
├── src/
│   ├── config.py               # env-driven settings
│   ├── db.py                   # pyexasol helpers (query_df, session, ping)
│   ├── sql/schema.sql          # conformed star schema
│   ├── data/generate_synthetic_data.py   # 3 fragmented channel feeds
│   ├── etl/load.py             # normalise + UNIFY into FACT_SALES
│   └── analytics/
│       ├── segmentation.py     # RFM via NTILE (in Exasol)
│       ├── forecasting.py      # demand forecast (Ridge + seasonality)
│       └── churn.py            # churn prob + CLV + priority
├── app/
│   ├── Home.py                 # KPIs + channel mix
│   └── pages/                  # the three modules
├── tests/smoke.py              # offline smoke tests
└── docs/ARCHITECTURE.md
```

---

## Deliverables checklist (ExaThon)

- [x] Public GitHub repo (MIT) — this repo
- [x] Clean README with setup & run instructions
- [x] Uses Exasol Personal as the data platform
- [x] Synthetic data only (no proprietary/employer data)
- [x] Reproducible pipeline + smoke tests
- [ ] Pitch deck (PDF/PPT) — outline in [docs/pitch-outline.md](docs/pitch-outline.md)
- [ ] Demo video (≤3 min)

---

## License

[MIT](LICENSE) © 2026 Arya Jawarkar
