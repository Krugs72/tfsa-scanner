"""Full-size test of the company-data step (Nov 24 Yahoo crumb fix)."""
import sys, time
sys.path.insert(0, ".")
import scanner

# 1) Does the direct fallback give the same numbers as yfinance?
for t in ["AAPL", "FIX", "RY.TO", "KDP", "XEQT.TO"]:
    a = scanner.get_info(t); b = scanner.get_info_direct(t)
    diffs = []
    for k in scanner.INFO_KEYS:
        x, y = a.get(k), b.get(k)
        if isinstance(x, (int, float)) and isinstance(y, (int, float)) and x and abs(x - y) / abs(x) < 0.02:
            continue
        if x != y:
            diffs.append(f"{k}: yf={x} direct={y}")
    print(f"[compare {t}] {len(diffs)} differences", "; ".join(diffs)[:600])

# 2) The whole universe at the real scan's pace
tickers = scanner.build_universe(False)
print(len(tickers), "tickers")
t0 = time.time()
for i, t in enumerate(tickers, 1):
    scanner.get_info(t)
    time.sleep(0.4)
    if i % 100 == 0:
        print(f"  {i}/{len(tickers)} {scanner.INFO_STATS} {time.time()-t0:.0f}s", flush=True)
print("FINAL", scanner.INFO_STATS, f"{time.time()-t0:.0f}s")
print(scanner.info_coverage_note()[0])
