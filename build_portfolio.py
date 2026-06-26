#!/usr/bin/env python3
import os
import json
import datetime as dt
import requests

try:
    import yfinance as yf
except ImportError:
    yf = None

# Config mapping & colors to match styling
CATEGORY_MAP = {
    "mf": "Mutual Funds",
    "equity": "Direct Equity",
    "etf": "Commodity & Sector ETFs",
    "us_etf": "International ETFs",
}
CATEGORY_COLORS = {
    "Mutual Funds": "#3ddc84",
    "Direct Equity": "#c9a45c",
    "Commodity & Sector ETFs": "#5c8f9c",
    "International ETFs": "#8c9089",
}

def fetch_amfi_navs():
    """Download AMFI's daily NAV file and return {scheme_code: nav}."""
    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    navs = {}
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        for line in resp.text.splitlines():
            parts = line.split(";")
            if len(parts) >= 5 and parts[0].strip().isdigit():
                code = parts[0].strip()
                try:
                    nav = float(parts[4].strip())
                    navs[code] = nav
                except ValueError:
                    continue
    except Exception as e:
        print(f"Warning: AMFI NAV fetch failed: {e}")
    return navs

def fetch_equity_prices(symbols_ns, symbols_us):
    """Fetch latest prices via yfinance for NSE (.NS) and US tickers, plus USD/INR."""
    prices = {}
    usd_inr = 83.5 # Fallback exchange rate
    
    if yf is None:
        print("Warning: yfinance is not installed!")
        return prices, usd_inr

    all_tickers = [s + ".NS" for s in symbols_ns] + symbols_us + ["USDINR=X"]
    if not all_tickers:
        return prices, usd_inr

    try:
        data = yf.Tickers(" ".join(all_tickers))
        for t in all_tickers:
            try:
                fast = data.tickers[t].fast_info
                price = fast.get("lastPrice") or fast.get("last_price") or fast.get("regularMarketPrice")
                if price is not None:
                    if t == "USDINR=X":
                        usd_inr = float(price)
                    else:
                        key = t[:-3] if t.endswith(".NS") else t
                        prices[key] = float(price)
            except Exception as e:
                print(f"Failed to fetch price for ticker {t}: {e}")
                continue
    except Exception as e:
        print(f"Warning: yfinance fetch failed: {e}")
    return prices, usd_inr

def compile_portfolio():
    # 1. Load holdings
    base_dir = os.path.dirname(os.path.abspath(__file__))
    holdings_path = os.path.join(base_dir, "holdings.json")
    if not os.path.exists(holdings_path):
        raise FileNotFoundError(f"Holdings file not found at {holdings_path}")

    with open(holdings_path, "r", encoding="utf-8") as f:
        holdings = json.load(f)

    # 2. Separate assets for fetching
    mf_symbols = [h["symbol"] for h in holdings if h["type"] == "mf"]
    equity_symbols = [h["symbol"] for h in holdings if h["type"] in ("equity", "etf")]
    us_symbols = [h["symbol"] for h in holdings if h["type"] == "us_etf"]

    # 3. Retrieve live data
    navs = fetch_amfi_navs()
    eq_prices, usd_inr = fetch_equity_prices(equity_symbols, us_symbols)

    # 4. Perform calculations
    calculated = []
    total_invested = 0
    total_current = 0

    for h in holdings:
        price = None
        live = False

        if h["type"] == "mf":
            price = navs.get(h["symbol"])
        else:
            price = eq_prices.get(h["symbol"])

        if price is not None:
            live = True
            if h["type"] == "us_etf":
                current_value_usd = price * h["qty"]
                current_value = current_value_usd * usd_inr
            else:
                current_value_usd = None
                current_value = price * h["qty"]
        else:
            current_value_usd = None
            current_value = h["invested"] # fallback

        gain = current_value - h["invested"]
        gain_pct = (gain / h["invested"] * 100) if h["invested"] else 0

        total_invested += h["invested"]
        total_current += current_value

        calculated.append({
            "name": h["name"],
            "symbol": h["symbol"],
            "type": h["type"],
            "qty": h["qty"],
            "invested": h["invested"],
            "currentPrice": price,
            "currentValue": current_value,
            "currentValueUSD": current_value_usd,
            "gain": gain,
            "gainPct": gain_pct,
            "live": live,
            "category": CATEGORY_MAP[h["type"]]
        })

    # Add allocation %
    for c in calculated:
        c["allocationPct"] = (c["currentValue"] / total_current * 100) if total_current else 0

    # Overall gains
    total_gain = total_current - total_invested
    total_gain_pct = (total_gain / total_invested * 100) if total_invested else 0
    total_gain_class = "pos" if total_gain >= 0 else "neg"
    total_gain_sign = "+" if total_gain >= 0 else "−"

    # Category grouping
    category_totals = {cat: 0.0 for cat in CATEGORY_MAP.values()}
    for c in calculated:
        category_totals[c["category"]] += c["currentValue"]

    # 5. Build SVG Donut arcs
    CIRCUMFERENCE = 502.65
    accumulated_length = 0
    arcs_html = []
    legend_html = []
    
    order = ["Mutual Funds", "Direct Equity", "Commodity & Sector ETFs", "International ETFs"]
    for cat in order:
        amt = category_totals[cat]
        pct = (amt / total_current * 100) if total_current else 0
        color = CATEGORY_COLORS[cat]

        if pct > 0:
            length = (pct / 100) * CIRCUMFERENCE
            arcs_html.append(
                f'<circle r="80" fill="none" stroke="{color}" stroke-width="26" '
                f'stroke-dasharray="{length:.2f} {CIRCUMFERENCE}" '
                f'stroke-dashoffset="-{accumulated_length:.2f}"></circle>'
            )
            accumulated_length += length

        # Legend items html
        legend_html.append(f"""
          <li>
            <span class="swatch-label">
              <span class="swatch" style="background: {color}"></span>
              {cat}
            </span>
            <span>
              <span class="pct">{pct:.2f}%</span>
              <span class="amt">₹{amt:,.2f}</span>
            </span>
          </li>""")

    # 6. Build holdings table rows
    table_rows = []
    # Default sort by allocation percentage descending
    sorted_holdings = sorted(calculated, key=lambda x: -x["allocationPct"])
    for h in sorted_holdings:
        cls = "pos" if h["gain"] >= 0 else "neg"
        sign = "+" if h["gain"] >= 0 else "−"
        live_tag = "" if h["live"] else ' <span style="color:var(--faint);font-size:10px;">(cached)</span>'
        
        if h["type"] == "us_etf" and h["currentValueUSD"] is not None:
            value_text = f"${h['currentValueUSD']:,.2f} (₹{h['currentValue']:,.2f})"
        else:
            value_text = f"₹{h['currentValue']:,.2f}"

        unit_label = "units" if h["type"] == "mf" else "shares"

        table_rows.append(f"""
              <tr>
                <td>
                  <span class="asset-name">{h['name']}{live_tag}</span>
                  <span class="asset-symbol">{h['symbol']} · {h['qty']} {unit_label}</span>
                </td>
                <td>{h['allocationPct']:.2f}%</td>
                <td>₹{h['invested']:,.2f}</td>
                <td>{value_text}</td>
                <td class="{cls}">{sign}{abs(h['gainPct']):.2f}%</td>
              </tr>""")

    # Table footer
    table_footer = f"""
            <tr>
              <td>Total</td>
              <td>100.00%</td>
              <td>₹{total_invested:,.2f}</td>
              <td>₹{total_current:,.2f}</td>
              <td class="{total_gain_class}">{total_gain_sign}{abs(total_gain_pct):.2f}%</td>
            </tr>"""

    # 7. Portfolio Metrics
    largest = max(calculated, key=lambda x: x["allocationPct"])
    best = max(calculated, key=lambda x: x["gainPct"])
    best_cls = "pos" if best["gainPct"] >= 0 else "neg"

    # Compiled time
    IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
    now_str = dt.datetime.now(IST).strftime("%d %b %Y, %I:%M %p")

    # 8. Load template and replace
    template_path = os.path.join(base_dir, "index.template.html")
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template file not found at {template_path}")

    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    replacements = {
        "{{TOTAL_INVESTED}}": f"{total_invested:,.2f}",
        "{{TOTAL_CURRENT}}": f"{total_current:,.2f}",
        "{{TOTAL_GAIN}}": f"{abs(total_gain):,.2f}",
        "{{TOTAL_GAIN_PCT}}": f"{abs(total_gain_pct):.2f}",
        "{{TOTAL_GAIN_CLASS}}": total_gain_class,
        "{{TOTAL_GAIN_SIGN}}": total_gain_sign,
        "{{DONUT_ARCS}}": "\n".join(arcs_html),
        "{{LEGEND_ITEMS}}": "".join(legend_html),
        "{{TABLE_ROWS}}": "".join(table_rows),
        "{{TABLE_FOOTER}}": table_footer,
        "{{LARGEST_HOLDING_NAME}}": largest["name"],
        "{{LARGEST_HOLDING_PCT}}": f"{largest['allocationPct']:.2f}",
        "{{BEST_PERFORMER_NAME}}": best["name"],
        "{{BEST_PERFORMER_PCT}}": f"{best['gainPct']:.2f}",
        "{{BEST_PERFORMER_CLASS}}": best_cls,
        "{{TOTAL_HOLDINGS_COUNT}}": str(len(calculated)),
        "{{COMPILED_TIME}}": now_str,
        "{{INITIAL_DATA_JSON}}": json.dumps(calculated, indent=2)
      }

    for placeholder, val in replacements.items():
        template = template.replace(placeholder, val)

    # Save to index.html
    output_path = os.path.join(base_dir, "index.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(template)

    print(f"Portfolio successfully compiled to {output_path} at {now_str}!")

if __name__ == "__main__":
    compile_portfolio()
