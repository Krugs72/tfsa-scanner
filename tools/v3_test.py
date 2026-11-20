"""Nov 20, 2026: run scoring v3 in quick mode on holdings + watchlist + a test list, print results.
Runs on GitHub Actions via 'One-off research script'; nothing is committed."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config, scanner
import pandas as pd
TEST = ["NVDA", "GOOGL", "MSFT", "CTSH", "BTO.TO", "LUG.TO", "KNT.TO", "URBN", "ALSN", "NXPI",
        "COP", "AMD", "ECPG", "VIRT", "PLMR", "T.TO", "BRK-B", "META", "AMZN"]
config.WATCHLIST = list(dict.fromkeys(list(getattr(config, "WATCHLIST", [])) + TEST))
config.REPORT_DIR = "/tmp/v3"
scanner.main(quick=True)
d = pd.read_csv("/tmp/v3/latest.csv")
cols = ["ticker", "total", "agree", "passed", "signal", "verdict", "trend", "pct_vs_band", "cowan",
        "buffett", "lynch", "growth", "greenblatt", "graham", "dca_zone", "pick_ok", "red_flags"]
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30); pd.set_option("display.max_colwidth", 45)
print(d[d.ticker.isin(TEST)][[c for c in cols if c in d]].to_string(index=False))
