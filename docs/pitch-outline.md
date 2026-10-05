# Pitch outline (for deck + 3-min demo video)

Target: 10–12 slides / 3-minute video. Map each beat to the Stage-1 rubric.

## 1. Hook / problem (Innovation & impact — 25%)
- A retailer sells on its website, in stores, and on a marketplace.
- Each channel's data looks different (columns, date formats, gross vs net).
- Result: **nobody can answer "what should we stock / who should we keep" across
  all channels** — this is *sales fragmentation*, the heart of the track.

## 2. Who has the problem & why (deliverable: problem statement)
- Category managers, CRM/retention teams, demand planners.
- Today they stitch spreadsheets per channel; decisions are late and partial.

## 3. The idea
- One unified Exasol warehouse → one `FACT_SALES` → three decisions.
- Show the architecture diagram (docs/ARCHITECTURE.md).

## 4. Effective use of Exasol (25% — spend real time here)
- Three fragmented feeds reconciled into a conformed star schema.
- RFM via `NTILE` window functions; churn features via one in-DB `GROUP BY`;
  demand aggregated in Exasol. "The warehouse is the product."

## 5. Live demo (practice until it's tight)
1. Home: unified KPIs + channel revenue mix.
2. Demand Forecast: pick channels, show 30-day forecast with band → PO decision.
3. Customer Segments: Champions vs At-Risk (high value) → targeted offers.
4. Churn & CLV: risk × value scatter → the retention priority list.

## 6. Technical excellence (20%) + design/UX (15%)
- Explainable models, out-of-fold churn scores (no leakage), seasonal forecast.
- Clean multipage dashboard, graceful "not connected" setup guidance.

## 7. Reproducibility & open source (10% + 5%)
- `docker compose up` + 4 commands. Seeded synthetic data. Smoke tests. MIT.

## 8. Impact / ask
- Quantify: revenue sitting in "At Risk (high value)", forecasted demand to
  pre-position inventory. Close with the roadmap (real connectors, more channels).

---
### Recording tips
- Keep it ≤ 3:00. Pre-load data so the demo is instant.
- Narrate decisions, not clicks ("this ₹X of at-risk revenue is who we'd email").
- Show the fragmented CSVs for 3 seconds — it makes the unification land.
