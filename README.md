# Portfolio — Abubackar Siddiq

A clean, single-page website for viewing my investment portfolio — with live prices.

**Live:** https://abubackar-siddiq-s.github.io/Investment_Portfolio/ **(or)** https://abubackar-portfolio.netlify.app/

## About

This is a personal portfolio tracker — built purely for clear, organized viewing of holdings, allocation, and returns. It is not a pitch deck or investor report.

Prices update automatically: a GitHub Actions workflow runs on a schedule, pulls live data, and rebuilds the page — no manual price entry required.

## Contents

- Portfolio summary (invested, current value, gain/loss, returns)
- Asset allocation (donut chart + legend)
- Holdings table (allocation %, invested, current value, gain/loss %)
- Portfolio metrics (largest holding, best performer, holding count)
- Last-updated timestamp (IST)

## How it works

- `holdings.json` — source of truth for what I own: name, symbol, type, quantity, and amount invested. This is the **only** file I edit when I buy or sell.
- `build_portfolio.py` — reads `holdings.json`, fetches live prices, computes allocation/gain figures, and renders the final page.
  - **Mutual funds** — NAV from AMFI's daily NAV file (`amfiindia.com/spages/NAVAll.txt`), matched by scheme code.
  - **Equity & domestic ETFs** — live price via `yfinance` (NSE, `.NS` suffix).
  - **International ETFs** — live price via `yfinance` (US tickers), converted to INR using the live USD/INR rate.
- `index.template.html` — static layout and styling (the "wealth terminal" dark UI: glassmorphism cards, animated SVG donut chart, sortable table). Placeholders in this file are filled in by the build script.
- `index.html` — the generated output. This is what's actually deployed; don't edit it by hand, it gets overwritten on every run.
- `.github/workflows/` — schedules `build_portfolio.py` to run automatically and commits the refreshed `index.html`.

If a live price can't be fetched for a holding, that row falls back to its invested amount and is marked accordingly, rather than showing a stale or broken value.

## Updating my holdings

When I buy or sell, I only touch `holdings.json` — updating `qty` and `invested` for the relevant entry (or adding/removing an entry). Everything else — prices, allocation %, gain/loss, chart, metrics — is recalculated automatically on the next scheduled run.

## Tech

- Single static `index.html`, generated from `index.template.html` by `build_portfolio.py`
- No external libraries, CSS, or JS frameworks — vanilla HTML/CSS/SVG
- Semantic, accessible markup
- Print-friendly (exports cleanly to PDF)
- Python (`requirements.txt`) for the build/data-fetch script, run via GitHub Actions

## Run locally

```bash
pip install -r requirements.txt
python build_portfolio.py
```

Then open the generated `index.html` in a browser — no build step or server required beyond that.

## Deploy

Hosted on [Netlify](https://www.netlify.com/) and GitHub Pages. Any static host works since the deployed artifact is a single HTML file.

## Disclaimer

This is a personal tracking tool, not financial advice. Figures reflect my own holdings and may rely on third-party data (AMFI, Yahoo Finance) that can occasionally be delayed or unavailable.
