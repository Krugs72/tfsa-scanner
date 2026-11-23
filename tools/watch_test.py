"""Nov 23, 2026: check close watch rows (incl. TSLA, SPCX) and SPCX/TSLA scores."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd, scanner
rows = scanner.close_watch()
w = pd.DataFrame(rows)
pd.set_option("display.width", 250)
print(w[["ticker", "price", "chg_1d", "status", "vs_band", "reclaim_price", "to_reclaim", "from_high", "bottom_signs"]].to_string(index=False))
print("\n".join(scanner.close_watch_lines(rows)))
