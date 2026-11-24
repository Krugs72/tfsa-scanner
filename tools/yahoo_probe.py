"""Probe why Yahoo company data (Ticker.info) fails from GitHub Actions, and test fixes."""
import inspect, json, re, time, traceback
import yfinance as yf

print("yfinance", yf.__version__)
from yfinance import data as yd
src = inspect.getsource(yd)
for name in re.findall(r"\n    def (\w+)\(", src):
    print("  YfData." + name)
print("--- crumb-related source ---")
for m in re.finditer(r"\n    def (_get_crumb\w*|_get_cookie\w*|_set_cookie_strategy|get|_make_request)\(.*?(?=\n    def |\Z)", src, re.S):
    print(m.group(0)[:1800])
    print("....")

T = ["AAPL", "MSFT", "FIX", "KDP", "RY.TO", "SHOP.TO", "FSLR", "RDN", "ENVA", "PRG"]


def try_info(label):
    ok = 0
    for t in T:
        try:
            i = yf.Ticker(t).info or {}
            if i.get("trailingPE") or i.get("marketCap"):
                ok += 1
        except Exception as e:
            print("   ", t, type(e).__name__, str(e)[:120])
        time.sleep(0.3)
    print(f"[{label}] info ok {ok}/{len(T)}")
    return ok


try_info("plain")

# Reset the cached crumb/cookie and switch strategy
d = yd.YfData()
for strat in ("csrf", "basic"):
    try:
        if hasattr(d, "_set_cookie_strategy"):
            d._set_cookie_strategy(strat)
        d._crumb = None
        d._cookie = None
        try_info("strategy " + strat)
    except Exception:
        traceback.print_exc()

# Raw curl_cffi with our own crumb
from curl_cffi import requests as cr
for imp in ("chrome", "safari", "firefox"):
    try:
        s = cr.Session(impersonate=imp)
        s.get("https://fc.yahoo.com", timeout=15, allow_redirects=True)
        crumb = s.get("https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=15).text
        print(f"[raw {imp}] crumb={crumb[:20]!r} cookies={list(s.cookies.keys())}")
        ok = 0
        for t in T:
            for host in ("query1", "query2"):
                r = s.get(f"https://{host}.finance.yahoo.com/v10/finance/quoteSummary/{t}",
                          params={"modules": "summaryDetail,financialData,defaultKeyStatistics,assetProfile,price",
                                  "crumb": crumb}, timeout=15)
                if r.status_code == 200:
                    ok += 1
                    break
                else:
                    print("   ", imp, host, t, r.status_code, r.text[:100])
            time.sleep(0.3)
        print(f"[raw {imp}] quoteSummary ok {ok}/{len(T)}")
        r = s.get("https://query1.finance.yahoo.com/v7/finance/quote",
                  params={"symbols": ",".join(T), "crumb": crumb}, timeout=15)
        n = len((r.json().get("quoteResponse") or {}).get("result") or []) if r.status_code == 200 else 0
        print(f"[raw {imp}] v7 quote status {r.status_code} results {n}", r.text[:150] if r.status_code != 200 else "")
        if n:
            print("   keys:", sorted(r.json()["quoteResponse"]["result"][0].keys())[:80])
    except Exception:
        traceback.print_exc()

# Endpoints that don't need a crumb
s = cr.Session(impersonate="chrome")
r = s.get("https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/AAPL",
          params={"type": "annualNetIncome,annualTotalRevenue,trailingPeRatio,trailingMarketCap",
                  "period1": 1600000000, "period2": int(time.time())}, timeout=15)
print("[timeseries no crumb]", r.status_code, r.text[:200])
for t in ("AAPL", "RY.TO"):
    try:
        tk = yf.Ticker(t)
        fi = tk.fast_info
        print(f"[fast_info {t}] mcap={fi.get('marketCap')} last={fi.get('lastPrice')}")
        inc = tk.get_income_stmt(freq="yearly")
        print(f"[income_stmt {t}] shape={getattr(inc, 'shape', None)}")
    except Exception as e:
        print(f"[alt {t}]", type(e).__name__, str(e)[:150])
