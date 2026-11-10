"""
TFSA Scanner v2 - scores the S&P 500 + TSX Composite + S&P 400 mid caps + S&P 600 small caps (plus your holdings and
watchlist) with five great investors' rules, each worth 0-20 points:

  Cowan      - trend: 20-week SMA / 21-week EMA "bull market support band"
  Buffett    - quality + value: P/E, ROE, debt, margins, free cash flow
  Lynch      - growth at a reasonable price (PEG)
  O'Neil     - CAN SLIM: earnings + sales speeding up, near highs, beating the market
  Greenblatt - Magic Formula: high return on capital + cheap (ranked vs everyone)

Plus a market-weather check (Fed, jobs, yield curve, Bitcoin) and news/Reddit
sentiment on the top picks.

Run:      python scanner.py            (full scan)
          python scanner.py --quick    (holdings + watchlist only, no sentiment)
Output:   reports/latest.md (reads nicely in the GitHub phone app),
          reports/latest.html, reports/latest.csv, and dated copies.

Research tool only. It never trades. Not financial advice.
"""
import datetime as dt
import html
import io
import os
import re
import sys
import time
import xml.etree.ElementTree as ET

import pandas as pd
import requests

import config

UA = {"User-Agent": "Mozilla/5.0 (tfsa-scanner personal research script)"}
TODAY = dt.date.today()


# ================================================================ universe ===
def sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = pd.read_html(io.StringIO(requests.get(url, headers=UA, timeout=30).text))
    syms = tables[0]["Symbol"].astype(str)
    return [s.replace(".", "-") for s in syms]


def _wiki_symbols(url):
    tables = pd.read_html(io.StringIO(requests.get(url, headers=UA, timeout=30).text))
    for t in tables:
        col = next((c for c in t.columns if str(c).lower() in ("symbol", "ticker", "ticker symbol")), None)
        if col is not None and len(t) > 300:
            return [str(x).replace(".", "-") for x in t[col]]
    return []


def sp400_tickers():   # US mid caps
    return _wiki_symbols("https://en.wikipedia.org/wiki/List_of_S%26P_400_companies")


def sp600_tickers():   # US small caps: where a lot of future growth stocks live
    return _wiki_symbols("https://en.wikipedia.org/wiki/List_of_S%26P_600_companies")


def tsx_tickers():
    url = "https://en.wikipedia.org/wiki/S%26P/TSX_Composite_Index"
    tables = pd.read_html(io.StringIO(requests.get(url, headers=UA, timeout=30).text))
    for t in tables:
        col = next((c for c in t.columns if str(c).lower() in ("ticker", "symbol")), None)
        if col is not None and len(t) > 150:
            return [str(s).strip().replace(".", "-") + ".TO" for s in t[col]]
    return []


def build_universe(quick=False):
    names = list(dict.fromkeys(config.HOLDINGS + config.WATCHLIST))
    if quick or not config.SCAN_UNIVERSE:
        return names
    for fn in (sp500_tickers, tsx_tickers, sp400_tickers, sp600_tickers):
        try:
            got = fn()
            print(f"  {fn.__name__}: {len(got)} tickers")
            names += got
        except Exception as e:
            print(f"  {fn.__name__} failed ({e}); continuing without it")
    return list(dict.fromkeys(names))


# ==================================================================== data ===
def download_weekly(tickers):
    """Weekly closes for many tickers in one go. Returns {ticker: Series}."""
    import yfinance as yf
    out = {}
    for i in range(0, len(tickers), 100):
        chunk = tickers[i:i + 100]
        df = yf.download(chunk, period="2y", interval="1wk", auto_adjust=True,
                         progress=False, group_by="ticker", threads=True)
        for t in chunk:
            try:
                s = df[t]["Close"] if len(chunk) > 1 else df["Close"]
                if isinstance(s, pd.DataFrame):
                    s = s.iloc[:, 0]
                s = s.dropna()
                if len(s) > 10:
                    out[t] = s
            except Exception:
                pass
        time.sleep(2)
    return out


INFO_KEYS = ["shortName", "quoteType", "sector", "trailingPE", "forwardPE",
             "returnOnEquity", "returnOnAssets", "debtToEquity", "profitMargins",
             "freeCashflow", "marketCap", "earningsGrowth", "earningsQuarterlyGrowth",
             "revenueGrowth", "trailingPegRatio", "pegRatio", "enterpriseToEbitda",
             "fiftyTwoWeekHigh", "dividendYield", "currency"]


def get_info(ticker, tries=3):
    import yfinance as yf
    for n in range(tries):
        try:
            info = yf.Ticker(ticker).info or {}
            return {k: info.get(k) for k in INFO_KEYS}
        except Exception as e:
            if "Too Many Requests" in str(e) or "429" in str(e):
                time.sleep(20 * (n + 1))
            else:
                time.sleep(2)
    return {}


def get_fred(series_id):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    r = requests.get(url, headers=UA, timeout=20)   # FRED often blocks cloud runners
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = ["date", "value"]
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna().set_index("date")["value"]


def get_btc_weekly():
    """Bitcoin weekly closes. Yahoo first (no key), CoinGecko as backup."""
    try:
        import yfinance as yf
        s = yf.download("BTC-USD", period="2y", interval="1wk", auto_adjust=True,
                        progress=False)["Close"]
        if isinstance(s, pd.DataFrame):
            s = s.iloc[:, 0]
        s = s.dropna()
        if len(s) > 30:
            return s
    except Exception:
        pass
    url = ("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
           "?vs_currency=usd&days=730&interval=daily")
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    p = r.json()["prices"]
    s = pd.Series([x[1] for x in p], index=pd.to_datetime([x[0] for x in p], unit="ms"))
    return s.resample("W-FRI").last().dropna()


# ================================================================ scoring ===
def cowan(closes):
    """Trend vs the bull market support band. 0-20 points."""
    if len(closes) < config.BAND_SLOW + 2:
        return {"trend": "Not enough history", "cowan": 0}
    price = float(closes.iloc[-1])
    sma = closes.rolling(config.BAND_FAST).mean()
    ema = closes.ewm(span=config.BAND_SLOW, adjust=False).mean()
    hi = pd.concat([sma, ema], axis=1).max(axis=1)
    lo = pd.concat([sma, ema], axis=1).min(axis=1)
    above = closes > hi * 1.02          # 2% buffer stops sideways chop from flip-flopping
    below = closes < lo * 0.98
    ext = price / float(sma.iloc[-1]) - 1
    n = config.RECLAIM_WEEKS
    reclaimed = bool(above.iloc[-1] and below.iloc[-(n + 1):-1].any())
    lost = bool(below.iloc[-1] and above.iloc[-(n + 1):-1].any())
    if ext >= config.BUBBLE_EXTENSION:
        trend, pts = "Overheated (40%+ above band)", 8
    elif reclaimed:
        trend, pts = "JUST RECLAIMED band", 20
    elif above.iloc[-1]:
        trend, pts = "Uptrend", 16
    elif lost:
        trend, pts = "JUST LOST band", 2
    elif not below.iloc[-1]:
        trend, pts = "Testing band", 10
    else:
        trend, pts = "Downtrend", 0
    lm = closes.rolling(config.LONG_MA_WEEKS).mean().iloc[-1]
    w26 = closes.iloc[-27] if len(closes) > 27 else closes.iloc[0]
    return {"price": round(price, 2), "pct_vs_band": round(ext * 100, 1),
            "above_200d": None if pd.isna(lm) else bool(price > lm),
            "ret_26w": round((price / float(w26) - 1) * 100, 1),
            "off_high_pct": round((price / float(closes.iloc[-52:].max()) - 1) * 100, 1),
            "trend": trend, "cowan": pts}


def is_fund(f):
    return f.get("quoteType") in ("ETF", "MUTUALFUND")


def buffett(f):
    if is_fund(f):
        return 14, "index/ETF"
    pts, why = 0, []
    pe = f.get("trailingPE")
    roe, de, pm, fcf = (f.get("returnOnEquity"), f.get("debtToEquity"),
                        f.get("profitMargins"), f.get("freeCashflow"))
    if pe and 0 < pe <= config.MAX_PE: pts += 5; why.append(f"P/E {pe:.0f}")
    if roe and roe >= config.MIN_ROE: pts += 5; why.append(f"ROE {roe:.0%}")
    if de is not None and de / 100 <= config.MAX_DEBT_TO_EQUITY: pts += 3; why.append("low debt")
    if pm and pm >= config.MIN_PROFIT_MARGIN: pts += 4; why.append(f"margin {pm:.0%}")
    if fcf and fcf > 0: pts += 3
    elif fcf is not None and fcf <= 0: why.append("burning cash")
    if not pe: why.append("no profits")
    return pts, ", ".join(why)


CYCLICAL = ("Basic Materials", "Energy")


def lynch(f):
    if is_fund(f):
        return 0, None
    peg = f.get("trailingPegRatio") or f.get("pegRatio")
    if not peg:
        pe, g = f.get("trailingPE"), f.get("earningsGrowth")
        if pe and g and g > 0:
            peg = pe / (g * 100)
    if not peg or peg <= 0:
        return 0, None
    pts = 20 if peg <= config.GOOD_PEG else 13 if peg <= 1.5 else 6 if peg <= 2 else 0
    # Lynch's own warning: miners/oil look cheapest at the top of their cycle,
    # because profits are temporarily huge. Cap the score so they don't dominate.
    if f.get("sector") in CYCLICAL:
        pts = min(pts, 10)
    return pts, round(peg, 2)


def oneil(f, tr, bench_ret):
    if is_fund(f):
        return 0
    pts = 0
    if (f.get("earningsQuarterlyGrowth") or 0) >= config.MIN_EPS_GROWTH: pts += 7
    if (f.get("revenueGrowth") or 0) >= config.MIN_SALES_GROWTH: pts += 4
    if tr.get("off_high_pct") is not None and tr["off_high_pct"] >= -config.NEAR_HIGH * 100: pts += 4
    if tr.get("ret_26w") is not None and bench_ret is not None and tr["ret_26w"] > bench_ret + 10: pts += 5
    return pts


def greenblatt_ranks(df):
    """Magic Formula: rank everyone on return on capital and earnings yield
    (skipping banks/insurers/utilities like Greenblatt does). 0-20 points."""
    ok = (~df["sector"].isin(["Financial Services", "Utilities"])) & df["is_stock"]
    roc = df["returnOnAssets"].where(ok)
    ey = (1 / df["enterpriseToEbitda"]).where(ok & (df["enterpriseToEbitda"] > 0))
    score = roc.rank(pct=True) + ey.rank(pct=True)
    return (score.rank(pct=True) * 20).fillna(0).round().astype(int)


# =============================================================== macro =====
def yahoo_weekly(sym):
    import yfinance as yf
    s = yf.download(sym, period="3y", interval="1wk", auto_adjust=True, progress=False)["Close"]
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0]
    return s.dropna()


def macro_weather():
    out, notes = {}, []
    try:
        # 3-month T-bill yield tracks the Fed's rate closely
        tb = yahoo_weekly("^IRX")
        cutting = tb.iloc[-1] < tb.iloc[-27] - 0.2
        hiking = tb.iloc[-1] > tb.iloc[-27] + 0.2
        notes.append(f"Short-term rates {tb.iloc[-1]:.2f}% - " + (
            "Fed has been cutting over the last 6 months" if cutting else
            "Fed has been hiking" if hiking else "Fed on hold"))
    except Exception as e:
        notes.append(f"Rate data unavailable ({e})")
    try:
        ur = get_fred("UNRATE")
        sahm = ur.iloc[-3:].mean() - ur.iloc[-12:].min()
        out["sahm"] = sahm
        notes.append(f"Unemployment {ur.iloc[-1]:.1f}% - " + (
            "RECESSION WARNING (Sahm rule triggered)" if sahm >= 0.5 else
            "jobs weakening" if sahm >= 0.3 else "jobs stable"))
    except Exception as e:
        notes.append("Jobs data unavailable this run (FRED blocked) - see the Sunday report")
    try:
        # 10-year minus 3-month yield (the curve the Fed's own recession model uses)
        ten, three = yahoo_weekly("^TNX"), yahoo_weekly("^IRX")
        yc = (ten - three).dropna()
        out["yc"] = yc.iloc[-1]
        notes.append(f"Yield curve (10y-3m) {yc.iloc[-1]:+.2f} - " + (
            "inverted (late cycle)" if yc.iloc[-1] < 0 else
            "recently un-inverted (has come before past recessions)" if yc.iloc[-104:].min() < 0 else "normal"))
    except Exception as e:
        notes.append(f"Yield curve unavailable ({e})")
    try:
        b = cowan(get_btc_weekly())
        out["btc"] = b
        notes.append(f"Bitcoin ${b['price']:,.0f} - {b['trend']} ({b['pct_vs_band']:+.1f}% vs 20-week)")
    except Exception as e:
        notes.append(f"Bitcoin data unavailable ({e})")
    risk = 0
    risk -= 2 if out.get("sahm", 0) >= 0.5 else 1 if out.get("sahm", 0) >= 0.3 else 0
    risk -= 1 if out.get("yc", 1) < 0 else 0
    if "btc" in out:
        risk += 1 if out["btc"]["cowan"] >= 16 else -1 if out["btc"]["cowan"] <= 2 else 0
    out["regime"] = "RISK-ON" if risk >= 1 else "RISK-OFF" if risk <= -2 else "NEUTRAL / CAUTIOUS"
    out["notes"] = notes
    return out


# ============================================================= sentiment ===
POS = set("beat beats upgrade upgraded surge soars soar rally record raise raised "
          "growth bullish breakout approval approved contract wins win partnership "
          "buyback outperform strong profit expands accumulate undervalued".split())
NEG = set("miss misses downgrade downgraded plunge plunges crash lawsuit dilution "
          "offering delay delayed cut cuts bearish fraud bankruptcy weak loss losses "
          "sell selloff short probe investigation recall overvalued warning".split())


def tone(texts):
    p = n = 0
    for t in texts:
        w = re.findall(r"[a-z]+", t.lower())
        p += sum(x in POS for x in w)
        n += sum(x in NEG for x in w)
    return round((p - n) / (p + n), 2) if p + n else 0.0


def sentiment(ticker, name):
    heads, posts = [], []
    try:
        q = requests.utils.quote(f'"{name}" stock when:7d')
        r = requests.get(f"https://news.google.com/rss/search?q={q}&hl=en-CA&gl=CA&ceid=CA:en",
                         headers=UA, timeout=20)
        junk = re.compile(r"stock price|quote|interactive stock chart|seasonal returns|"
                          r"stock forecast|historical prices|stock chart", re.I)
        heads = [h for h in (i.findtext("title") or "" for i in ET.fromstring(r.content).iter("item"))
                 if not junk.search(h)][:25]
    except Exception:
        pass
    time.sleep(1)
    try:
        base = ticker.split(".")[0]
        q = requests.utils.quote(f'"{base}" OR "{name}"')
        r = requests.get(f"https://www.reddit.com/r/{'+'.join(config.SUBREDDITS)}/search.json"
                         f"?q={q}&restrict_sr=1&sort=new&t=week&limit=50", headers=UA, timeout=20)
        posts = [p["data"]["title"] for p in r.json()["data"]["children"]]
    except Exception:
        pass
    time.sleep(2)
    return {"news_tone": tone(heads), "reddit_tone": tone(posts),
            "reddit_posts": len(posts),
            "buzz": "HIGH" if len(posts) >= 25 else "medium" if len(posts) >= 8 else "low",
            "headline": heads[0] if heads else ""}


# =============================================================== verdict ===
def verdict(r, regime):
    passes = r["passes"]
    if r["buffett"] >= 14 and r["cowan"] >= 10:
        v = "CORE"
    elif r["buffett"] >= 14:
        v = "WAIT FOR ENTRY"
    elif "RECLAIMED" in r["trend"] and passes >= 2:
        v = "EMERGING"
    elif r["oneil"] >= 14 and r["cowan"] >= 16:
        v = "EMERGING"
    elif "Overheated" in r["trend"]:
        v = "DON'T CHASE"
    elif r["buffett"] < 6 and r["cowan"] >= 16:
        v = "SPECULATIVE MOMENTUM"
    elif r["buffett"] < 6 and r["cowan"] <= 2:
        v = "AVOID FOR NOW"
    else:
        v = "WATCH"
    if regime == "RISK-OFF" and v in ("EMERGING", "SPECULATIVE MOMENTUM"):
        v += " (market risk-off)"
    return v


# =============================================================== signals ===
def cad_info(t):
    if t.endswith((".TO", ".V", ".NE", ".CN")):
        return "CAD", ""
    cdr = config.CDR_MAP.get(t)
    if cdr:
        return "CDR", f"CAD version: {cdr} (Cboe Canada CDR)"
    return "USD", "US-only: 1.5% FX fee each way"


def signal(r, regime, held):
    """Rule-based alerts. Research leads, not orders."""
    trend = r["trend"]
    up = ("RECLAIMED" in trend) or (trend == "Uptrend")
    if held:
        if "JUST LOST" in trend:
            return "EXIT WATCH - just fell below trend band"
        if "Overheated" in trend:
            return "TRIM WATCH - overheated, consider taking some profit"
        if trend == "Downtrend" and r["buffett"] < 6 and r["is_stock"]:
            return "EXIT WATCH - weak business in a downtrend"
        if "RECLAIMED" in trend:
            return "ADD WATCH - trend just turned back up"
        return ""
    if (up and r["passes"] >= config.ENTRY_MIN_PASSES
            and r["buffett"] >= config.ENTRY_MIN_BUFFETT and regime != "RISK-OFF"):
        strong = "RECLAIMED" in trend and r["passes"] >= 4
        return "STRONG ENTRY SIGNAL" if strong else "ENTRY SIGNAL"
    return ""


# ================================================================ report ===
def _pct(x):
    try:
        return f"{float(x) * 100:+.0f}%" if x == x and x is not None else "n/a"
    except Exception:
        return "n/a"


def add_growth_score(df):
    """For a 24-year-old's long runway: reward fast-growing sales/earnings in an
    uptrend that's still a real business. 0-100."""
    rg = pd.to_numeric(df["rev_growth"], errors="coerce").fillna(0).clip(-0.5, 1.0)
    eg = pd.to_numeric(df["eps_growth"], errors="coerce").fillna(0).clip(-1, 2.0)
    score = (rg.rank(pct=True) * 30 + eg.rank(pct=True) * 20 +
             df["oneil"] * 1.0 + df["lynch"] * 0.5 + df["cowan"] * 0.75 + df["buffett"] * 0.25)
    # Miners/oil "growth" is mostly commodity prices, not the business: knock 15% off
    score = score.where(~df["sector"].isin(CYCLICAL), score * 0.85)
    df["growth_score"] = score.clip(upper=100).round().astype(int)
    return df


def growth_bullets(r):
    b, stats = [], []
    rg, eg, pe = r.get("rev_growth"), r.get("eps_growth"), r.get("pe")
    if rg == rg and rg is not None:
        stats.append(f"Sales {_pct(rg)}")
    if eg == eg and eg is not None:
        stats.append("Earnings 5x+ (low base, one-off?)" if eg > 5 else f"Earnings {_pct(eg)}")
    if pe == pe and pe:
        stats.append(f"P/E {pe:.0f}")
    if stats:
        b.append(" · ".join(stats))
    if "RECLAIMED" in str(r["trend"]):
        b.append("Just broke back above its trend line")
    elif r["trend"] == "Uptrend":
        b.append(f"Uptrend, {r['ret_26w']:+.0f}% in 6 months")
    if r["passed"]:
        b.append(f"Passes {r['passed']}")
    if r.get("sector") in ("Basic Materials", "Energy"):
        b.append("⚠️ Commodity-driven: rides metal/oil prices")
    return b


def write_brief(df, macro):
    """Short phone-friendly dashboard: top growth picks by Canada / US / Other."""
    held = set(config.HOLDINGS)
    ok = (~df.ticker.isin(held)) & df.is_stock.astype(bool) & \
         (df.cowan >= 10) & (~df.trend.astype(str).str.contains("Overheated")) & \
         (pd.to_numeric(df.rev_growth, errors="coerce").fillna(0) >= 0.10) & (df.buffett >= 6)
    g = df[ok].sort_values("growth_score", ascending=False)
    ca = g[g.currency.isin(["CAD"])].head(3)
    us = g[g.currency.isin(["USD", "CDR"])].head(3)
    other_t = [t for t in config.WATCHLIST if t in set(df.ticker)]
    other = df[df.ticker.isin(other_t) & (df.cowan >= 10)].sort_values("cowan", ascending=False).head(3)

    def block(d):
        out = []
        for i, (_, r) in enumerate(d.iterrows(), 1):
            sig = f" · 🔔 {r['signal']}" if isinstance(r["signal"], str) and "ENTRY" in r["signal"] else ""
            cad = f" · 🇨🇦 buy as {config.CDR_MAP[r['ticker']]}" if r["currency"] == "CDR" else \
                  (" · 💱 1.5% FX fee" if r["currency"] == "USD" else "")
            out.append(f"**{i}. {r['ticker']}** {str(r['name'])[:28]} · ${r['price']:,.2f} · "
                       f"Growth {r['growth_score']}/100{sig}{cad}")
            out += [f"   - {x}" for x in growth_bullets(r)[:4]]
        return out or ["_Nothing qualifies today._"]

    btc = macro.get("btc", {})
    lines = [f"# ☀️ Morning brief · {TODAY:%b %d}", "",
             f"**Market:** {macro['regime']}" + (f" · BTC ${btc['price']:,.0f} ({btc['trend']})" if btc else ""),
             "", "## 🇨🇦 Canada growth (no FX fee)"] + block(ca) + \
            ["", "## 🇺🇸 US growth"] + block(us) + \
            ["", "## 🌐 Other (metals, crypto, themes)"]
    for _, r in other.iterrows():
        lines.append(f"- **{r['ticker']}** ${r['price']:,.2f} · {r['trend']} ({r['pct_vs_band']:+.0f}% vs line)")
    if not len(other):
        lines.append("_Nothing in an uptrend._")
    lines += ["", "## 📌 Your holdings"]
    for _, r in df[df.ticker.isin(held)].iterrows():
        flag = f" · ⚠️ {r['signal'].split(' - ')[0]}" if isinstance(r["signal"], str) and r["signal"] else ""
        lines.append(f"- **{r['ticker']}** ${r['price']:,.2f} · {r['trend']} ({r['pct_vs_band']:+.0f}%){flag}")
    lines += ["", "_Research only, not financial advice._"]
    with open(os.path.join(config.REPORT_DIR, "brief.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def write_reports(df, macro):
    os.makedirs(config.REPORT_DIR, exist_ok=True)
    cols = ["ticker", "name", "price", "total", "passes", "passed", "signal", "new_signal",
            "currency", "cad_note", "verdict", "trend",
            "pct_vs_band", "cowan", "buffett", "lynch", "oneil", "greenblatt",
            "peg", "buffett_notes", "buzz", "news_tone", "reddit_tone", "headline", "is_stock",
            "sector", "rev_growth", "eps_growth", "pe", "mcap_b", "ret_26w", "growth_score"]
    df = df.reindex(columns=cols)
    df.to_csv(os.path.join(config.REPORT_DIR, "latest.csv"), index=False)
    df.to_csv(os.path.join(config.REPORT_DIR, f"scan-{TODAY}.csv"), index=False)

    held = df[df.ticker.isin(config.HOLDINGS)]
    signals = df[df.signal.astype(str).str.contains("ENTRY") & ~df.ticker.isin(config.HOLDINGS)]
    canada = df[df.currency.isin(["CAD", "CDR"]) & ~df.ticker.isin(config.HOLDINGS)
                & df.is_stock.astype(bool)].head(15)
    new = df[~df.ticker.isin(config.HOLDINGS)].head(config.REPORT_TOP_N)
    emerging = df[df.verdict.astype(str).str.startswith("EMERGING")
                  & ~df.ticker.isin(config.HOLDINGS)].head(10)

    def md_table(d):
        lines = ["| Ticker | Score | Passes | Verdict | Trend | Why |",
                 "|---|---|---|---|---|---|"]
        for _, r in d.iterrows():
            why = r["passed"] or "-"
            if isinstance(r.get("signal"), str) and r["signal"]:
                why = f"**{r['signal']}**" + (" 🆕" if r.get("new_signal") else "") + " · " + why
            if r.get("currency") in ("USD", "CDR"):
                why += f" · {r['cad_note']}"
            if isinstance(r["headline"], str) and r["headline"]:
                why += " · News: " + r["headline"][:80].replace("|", "/")
            lines.append(f"| **{r['ticker']}** {str(r['name'])[:22]} | {r['total']} | "
                         f"{r['passes']}/5 | {r['verdict']} | {r['trend']} "
                         f"({r['pct_vs_band']:+.0f}%) | {why} |")
        return "\n".join(lines)

    md = [f"# TFSA Scanner - {TODAY}", "",
          f"**Market weather: {macro['regime']}**", ""]
    md += [f"- {n}" for n in macro["notes"]]
    md += ["", f"Scanned {len(df)} stocks/ETFs. Each investor's rules are worth 20 points "
           f"(total out of 100). 'Passes' = how many investors' rules it meets "
           f"({config.PASS_MARK}+/20).", "",
           "## 🔔 Entry signals (passes 4+ investors, uptrend, decent business)",
           ("🆕 = new this week. Signals are research leads, not orders: check the news "
            "and size it small first."), "",
           md_table(signals.head(20)) if len(signals) else "_No entry signals this week._", "",
           "## Your holdings", md_table(held), "",
           "## 🇨🇦 Top Canadian picks (no FX fee: TSX-listed or CDR available)",
           md_table(canada) if len(canada) else "_None this week._", "",
           "## Emerging setups (trend just turned or fast growth + uptrend)",
           md_table(emerging) if len(emerging) else "_Nothing new this week._", "",
           f"## Top {config.REPORT_TOP_N} new ideas", md_table(new), "",
           "_Research tool only, not financial advice. Sentiment is a rough word count "
           "of headlines and Reddit titles: read the news yourself before acting._"]
    text = "\n".join(md)
    for name in ("latest.md", f"scan-{TODAY}.md"):
        with open(os.path.join(config.REPORT_DIR, name), "w", encoding="utf-8") as fh:
            fh.write(text)

    e = html.escape
    def h_table(d):
        hd = "".join(f"<th>{e(c)}</th>" for c in cols)
        rows = "".join("<tr>" + "".join(f"<td>{e(str(r[c]))}</td>" for c in cols) + "</tr>"
                       for _, r in d.iterrows())
        return f"<table><tr>{hd}</tr>{rows}</table>"
    page = (f"<!doctype html><meta charset='utf-8'><meta name='viewport' "
            f"content='width=device-width,initial-scale=1'><title>TFSA Scanner {TODAY}</title>"
            "<style>body{font-family:sans-serif;margin:16px}table{border-collapse:collapse;"
            "font-size:12px;width:100%}td,th{border-bottom:1px solid #ddd;padding:4px;"
            "text-align:left}th{background:#f3f3f3}</style>"
            f"<h1>TFSA Scanner {TODAY}</h1><h2>Market weather: {e(macro['regime'])}</h2><ul>"
            + "".join(f"<li>{e(n)}</li>" for n in macro["notes"]) + "</ul>"
            "<h2>Your holdings</h2>" + h_table(held) +
            "<h2>Emerging</h2>" + h_table(emerging) +
            "<h2>Top new ideas</h2>" + h_table(new) +
            "<p><small>Research only, not financial advice.</small></p>")
    with open(os.path.join(config.REPORT_DIR, "latest.html"), "w", encoding="utf-8") as fh:
        fh.write(page)
    write_brief(df, macro)
    try:
        from dashboard import write_dashboard
        write_dashboard(df, macro, os.path.join(config.REPORT_DIR, "dashboard.html"))
    except Exception as e:
        print("dashboard failed:", e)
    return os.path.join(config.REPORT_DIR, "latest.md")


# ================================================================== main ===
def main(quick=False):
    print("1/5 Market weather...")
    macro = macro_weather()
    for n in macro["notes"]:
        print("   ", n)

    print("2/5 Building stock list...")
    tickers = build_universe(quick)
    print(f"    {len(tickers)} tickers")

    print("3/5 Prices...")
    prices = download_weekly(list(dict.fromkeys(tickers + [config.BENCHMARK])))
    bench = cowan(prices[config.BENCHMARK])["ret_26w"] if config.BENCHMARK in prices else None

    print("4/5 Company numbers + trend...")
    rows = []
    for i, t in enumerate(tickers, 1):
        if t not in prices:
            continue
        tr = cowan(prices[t])
        f = get_info(t)
        if i % 25 == 0:
            print(f"    {i}/{len(tickers)}")
        time.sleep(0.4)
        b, bnotes = buffett(f)
        lp, peg = lynch(f)
        rows.append({"ticker": t, "name": f.get("shortName") or t, **tr,
                     "buffett": b, "buffett_notes": bnotes, "lynch": lp, "peg": peg,
                     "oneil": oneil(f, tr, bench), "is_stock": not is_fund(f),
                     "sector": f.get("sector"), "returnOnAssets": f.get("returnOnAssets"),
                     "enterpriseToEbitda": f.get("enterpriseToEbitda"),
                     "rev_growth": f.get("revenueGrowth"),
                     "eps_growth": f.get("earningsQuarterlyGrowth"),
                     "pe": f.get("trailingPE") or f.get("forwardPE"),
                     "mcap_b": round(f["marketCap"] / 1e9, 1) if f.get("marketCap") else None})
    df = pd.DataFrame(rows)
    df["greenblatt"] = greenblatt_ranks(df)
    inv = ["cowan", "buffett", "lynch", "oneil", "greenblatt"]
    label = {"cowan": "Cowan", "buffett": "Buffett", "lynch": "Lynch",
             "oneil": "O'Neil", "greenblatt": "Greenblatt"}
    df["total"] = df[inv].sum(axis=1)
    df["passes"] = (df[inv] >= config.PASS_MARK).sum(axis=1)
    df["passed"] = df.apply(lambda r: ", ".join(label[c] for c in inv if r[c] >= config.PASS_MARK), axis=1)
    df = df.sort_values(["passes", "total"], ascending=False).reset_index(drop=True)

    print("5/5 News + Reddit on holdings and top picks...")
    for c in ("buzz", "news_tone", "reddit_tone", "headline"):
        df[c] = pd.Series([""] * len(df), dtype=object)
    check = list(dict.fromkeys(
        [t for t in config.HOLDINGS if t in set(df.ticker)] +
        ([] if quick else list(df.ticker.head(config.SENTIMENT_TOP_N)))))
    for t in check:
        idx = df.index[df.ticker == t][0]
        s = sentiment(t, df.at[idx, "name"])
        for k in ("buzz", "news_tone", "reddit_tone", "headline"):
            df.at[idx, k] = s[k]
    df["verdict"] = df.apply(lambda r: verdict(r, macro["regime"]), axis=1)
    df["currency"] = df.ticker.map(lambda t: cad_info(t)[0])
    df["cad_note"] = df.ticker.map(lambda t: cad_info(t)[1])
    df["signal"] = df.apply(lambda r: signal(r, macro["regime"],
                                             r["ticker"] in config.HOLDINGS), axis=1)
    prev = set()
    try:
        old = pd.read_csv(os.path.join(config.REPORT_DIR, "latest.csv"))
        prev = set(old.loc[old["signal"].astype(str).str.len() > 0, "ticker"]) \
            if "signal" in old else set()
    except Exception:
        pass
    df = add_growth_score(df)
    df["new_signal"] = df.apply(lambda r: bool(r["signal"]) and r["ticker"] not in prev, axis=1)
    path = write_reports(df, macro)
    print(f"\nDone. Report: {path}")
    return path


if __name__ == "__main__":
    main(quick="--quick" in sys.argv)
