"""Simulate Yahoo killing the crumb mid-scan and check the scanner still gets company data."""
import sys
sys.path.insert(0, ".")
import scanner
from yfinance import data as yd

T = ["AAPL", "MSFT", "FIX", "KDP", "RY.TO", "SHOP.TO", "FSLR", "RDN", "ENVA", "PRG", "XEQT.TO", "CNQ.TO"]
d = yd.YfData()
got = 0
for t in T:
    d._crumb = "deadcrumb123"     # what Yahoo did on Nov 24: crumb no longer valid
    f = scanner.get_info(t)
    ok = scanner._has_data(f)
    got += ok
    print(t, "OK" if ok else "EMPTY", f.get("sector"), f.get("trailingPE"), f.get("dividendYield"))
print("FINAL", got, "/", len(T), scanner.INFO_STATS)
