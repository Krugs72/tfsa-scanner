"""Nov 25: scan crashed on a text P/E. Check cleaning + a quick scan end to end."""
import sys
sys.path.insert(0, ".")
import scanner
bad = {"trailingPE": "Infinity", "forwardPE": "12.5", "pegRatio": "-", "marketCap": {"raw": 5e9},
       "numberOfAnalystOpinions": 14.0, "sector": "Technology", "returnOnEquity": None}
c = scanner._clean(bad)
print("cleaned:", {k: v for k, v in c.items() if v is not None})
print("lynch on cleaned:", scanner.lynch(c), "buffett:", scanner.buffett(c)[0])
scanner.main(quick=True)
print("QUICK SCAN OK, skipped:", scanner.SKIPPED, scanner.INFO_STATS)
