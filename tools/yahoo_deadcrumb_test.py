"""Force yfinance's company data to fail (like Nov 24) and check the direct fallback carries the scan."""
import sys, time
sys.path.insert(0, ".")
import scanner, yfinance as yf

class Broken:
    def __init__(self, *a, **k): pass
    @property
    def info(self): raise Exception("HTTP Error 401: Invalid Crumb")
yf.Ticker = Broken

tickers = scanner.build_universe(False)[:150] + ["RY.TO", "XEQT.TO", "CNQ.TO"]
t0 = time.time()
for t in tickers:
    f = scanner.get_info(t)
    time.sleep(0.4)
print("FINAL", scanner.INFO_STATS, f"{time.time()-t0:.0f}s")
for t in ["AAPL", "RY.TO", "XEQT.TO"]:
    f = scanner.get_info_direct(t)
    print(t, {k: f.get(k) for k in ("sector", "trailingPE", "returnOnEquity", "dividendYield", "trailingPegRatio", "averageVolume", "quoteType")})
print(scanner.info_coverage_note()[0])
