# Wealth Transfer Strategy Comparison — MVP

Deterministic, citation-traced comparison of **seven** wealth-transfer strategies across three U.S. state regimes (NY, IL, TX) for tax year 2025.

> **Educational model — not tax or legal advice.** Every numeric output traces to the Internal Revenue Code, Treasury regulations, or state statute. Confirm with a qualified advisor before acting.

## What's modeled

Seven strategies, full lifecycle (contribution → accumulation → transfer → recipient treatment → terminal after-tax value):

1. **Taxable Brokerage** — donor-held, §1014 step-up at death, full estate inclusion
2. **Hold Until Death** — buy-and-hold to maximize §1014 step-up + §2010 unified credit
3. **§529 Plan** — tax-free growth, state deduction (NY $10K MFJ / IL $20K MFJ / TX none), §529(c)(4) estate exclusion, SECURE 2.0 §126 Roth rollover flag
4. **UGMA/UTMA** — completed gift, §1(g) kiddie tax, state age of majority
5. **Traditional IRA** — earned-income required, IRD under §691, SECURE 10-year rule
6. **Roth IRA (Custodial)** — earned-income required, §408A(d) tax-free corpus, never includible in donor's estate
7. **Trump Account** — OBBBA §70404 (Pub. L. 119-21, July 2025): $1,000 federal seed for 2025–2028 newborns, $5,000/yr parent cap, tax-deferred, restricted to U.S. equity index funds, age-18 access

Three state regimes: New York (with the §952/954 estate cliff), Illinois ($4M non-portable exemption), Texas (no income/estate tax, §1014(b)(6) community-property double step-up).

## Get a public web URL — fastest path (Vercel + Render)

This is the supported deployment path. Both services have free tiers; total setup time ≈ 10 minutes.

### 1. Push the repo to GitHub

```bash
cd wealth-transfer-mvp
git init && git add . && git commit -m "Initial commit"
gh repo create wealth-transfer-mvp --public --source=. --push
# or: create the repo via the GitHub UI and push manually
```

### 2. Deploy the backend on Render (free)

1. Sign in at <https://render.com> (free).
2. **New → Blueprint** → connect your GitHub repo.
3. Render reads `render.yaml` at the repo root, provisions a Python web service from `backend/`, runs the engine tests, and starts uvicorn.
4. Copy the resulting URL — e.g. `https://wealth-transfer-engine.onrender.com`.
5. Hit `https://<your-url>/healthz` — should return `{"status": "ok"}`.

Cold starts on the free tier take 30–60s after inactivity. Upgrade to the $7/month Starter plan if you want always-warm.

### 3. Deploy the frontend on Vercel (free)

1. Sign in at <https://vercel.com>.
2. **Add New → Project** → import your GitHub repo.
3. Set **Root Directory** to `frontend`.
4. Add an environment variable: `NEXT_PUBLIC_API_BASE` = your Render URL from step 2.
5. Click **Deploy**. Vercel builds Next.js and gives you a `https://<project>.vercel.app` URL.

Open that URL — that's your live product.

### 4. (Optional) Tighten CORS

Once you know the Vercel URL, set `CORS_ALLOW_ORIGINS` on Render to that exact origin (e.g. `https://your-app.vercel.app`) instead of `*`.

### Alternative — self-host with Docker

```bash
docker compose up --build
# backend: http://localhost:8000
# frontend: cd frontend && npm install && npm run dev → http://localhost:3000
```

## Run locally without Docker

### Backend (engine + FastAPI)

```bash
cd backend
pip install -e ".[dev]"
python -m pytest tests/                                    # 76 pinned tests
python -m uvicorn api:app --reload --port 8000
```

API is then live at <http://localhost:8000>:
- `GET /healthz`
- `GET /rules/version`
- `POST /compare` — body matches `DonorInputs` schema
- `POST /pdf` — same body; returns `application/pdf`

### Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev                                                # http://localhost:3000
```

The frontend reads `NEXT_PUBLIC_API_BASE` (defaults to `http://localhost:8000`).

### One-shot script

```bash
./run.sh                  # both services
./run.sh --backend-only   # skip frontend / npm
```

## Architecture

```
backend/
├── rules/
│   └── rules_2026.json           # Single source of truth — every number cited
├── engine/
│   ├── tax_context.py            # Decimal-only federal resolver
│   ├── inputs.py                 # Pydantic input schema with hard blocks
│   ├── citations.py              # Citation primitives + canonical strings
│   ├── regimes/                  # StateRegime ABC + NY / IL / TX
│   ├── strategies/               # Strategy ABC + seven concrete strategies
│   └── engine.py                 # Top-level orchestrator + recommendations
├── validators/
│   ├── aiwyn.py                  # Background regression validator (MCP, authless)
│   └── blue_j.py                 # Behind BLUEJ_API_KEY env flag
├── pdf_export.py                 # ReportLab Strategy Brief generator
├── api.py                        # FastAPI surface
└── tests/                        # 76 pinned scenarios

frontend/
├── app/
│   ├── layout.tsx
│   ├── globals.css
│   └── page.tsx                  # Form → dashboard
├── components/
│   ├── InputForm.tsx
│   ├── ComparisonTable.tsx       # Sorted by after-tax wealth to recipient
│   ├── AccumulationChart.tsx     # Line chart, toggleable strategies
│   ├── TaxDragWaterfall.tsx      # Pretax → after-tax bar waterfall
│   ├── TradeoffMatrix.tsx        # Radar chart of qualitative attributes
│   ├── RecommendationsPanel.tsx
│   └── CitationFootnote.tsx      # § hover with full authority detail
└── lib/
    ├── api.ts
    └── types.ts
```

### Determinism + audit trail

- All monetary math is `decimal.Decimal`. No `float`.
- Every parameter — exclusion amounts, bracket thresholds, deduction caps — lives in `rules_2026.json` with an IRC/Treasury reg/state-statute citation. The Python engine never hardcodes a number.
- Every `StrategyResult` carries a `citations: Citation[]` payload rendered as superscript footnotes in the UI.

### Acceptance criteria (status)

| Criterion | Status |
| --- | --- |
| Seven strategies × three states × three net-worth tiers return defensible numbers | ✅ 76 pinned tests |
| Every UI dollar traces to a JSON rule and a citation | ✅ |
| NY cliff produces a visible discontinuity | ✅ Pinned test + warning + UI surface |
| TX community-property double step-up beats NY/IL married | ✅ Pinned test |
| §529 5-year forward election changes year-1 gift footprint | ✅ Cited differently |
| Roth IRA path blocks correctly without earned income | ✅ Hard block surfaced in UI |
| Trump Account seed applies only to 2025–2028 newborns | ✅ Pinned test + warning |
| PDF export contains every citation referenced on-screen | ✅ Citations appendix |
| Public web URL deploy path documented end-to-end | ✅ Vercel + Render |

## External validators

- **Aiwyn Tax MCP** (default, authless) — fires as a FastAPI `BackgroundTask` after each `/compare`, replays the income-tax leg, logs `VALIDATION_DRIFT` if delta > $1.
- **Blue J** — REST API, behind `BLUEJ_API_KEY` env flag. Hidden in UI if unset.
- Estate/gift/GST legs are **not externally validated** by either source. They are pinned by hand-calculated tests.

## A note on Trump Account citations

The Trump Account was created by the One Big Beautiful Bill Act (Pub. L. 119-21), signed July 4, 2025. Treasury implementing regulations are still being issued as of the modeled year, so the specific subsection numbers cited (`§70404(b)`, `(c)`, `(g)`, etc.) and the proposed IRC §530A placeholder may shift as final regs publish. The MVP carries an in-app assumption note flagging this, and the structured rules file makes it a one-edit change to update parameters as guidance lands.

## Out of scope (schema reserved)

GRATs, IDGTs, SLATs, ILITs, CRTs/CLTs, §6166 active installment modeling, §§2701–2704 valuation discounts on closely-held interests, full QDOT mechanics, dynasty trusts, international donors/recipients.

## Versioning

The rules file is tagged with `tax_year` and `last_updated`. The UI footer surfaces the active version on every page load.
