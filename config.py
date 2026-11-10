"""
Edit this file to change what the scanner looks at.
Tickers use Yahoo Finance format: Canadian stocks end in .TO (TSX) or .V (Venture).
"""

# What you own right now. These always show at the top of the report.
HOLDINGS = ["VEQT.TO", "XDIV.TO", "MSTR", "INFQ", "IMSR", "CCO.TO", "CGL-C.TO"]  # MSTR held as Cboe Canada CDR; trend uses US MSTR

# Extra names to always include (on top of the S&P 500 + TSX Composite scan)
WATCHLIST = [
    "SLV", "PSLV.TO", "GLD", "WPM.TO", "PAAS.TO",      # silver / gold
    "CCJ", "NXE.TO", "OKLO", "SMR", "BWXT",            # nuclear / uranium
    "IONQ", "RGTI", "QBTS",                            # quantum
    "IBIT", "COIN",                                    # bitcoin-related
]

# Scan S&P 500 + TSX Composite + S&P 400 + S&P 600 (~1,700 stocks, ~30-40 min on GitHub)
SCAN_UNIVERSE = True

# Benchmark for "is this stock beating the market" (O'Neil relative strength)
BENCHMARK = "SPY"

# Reddit communities to scan for chatter
SUBREDDITS = ["stocks", "investing", "CanadianInvestor", "wallstreetbets",
              "Silverbugs", "UraniumSqueeze", "Bitcoin"]

# How many top-scoring new ideas get the slower news + Reddit check
SENTIMENT_TOP_N = 25
# How many top picks to list in the report
REPORT_TOP_N = 30

# --- Cowan trend rules ---
BAND_FAST = 20          # 20-week simple moving average
BAND_SLOW = 21          # 21-week exponential moving average
LONG_MA_WEEKS = 40      # ~200-day moving average
BUBBLE_EXTENSION = 0.40 # 40%+ above 20-week = overheated
RECLAIM_WEEKS = 3       # "just reclaimed the band" window

# --- Buffett rules ---
MAX_PE = 25
MIN_ROE = 0.15
MAX_DEBT_TO_EQUITY = 1.0
MIN_PROFIT_MARGIN = 0.10

# --- Lynch rule ---
GOOD_PEG = 1.0          # growth at a reasonable price

# --- O'Neil rules ---
MIN_EPS_GROWTH = 0.25   # quarterly earnings up 25%+ vs last year
MIN_SALES_GROWTH = 0.20
NEAR_HIGH = 0.15        # within 15% of 52-week high

# A stock "passes" an investor's rules at this many points out of 20
PASS_MARK = 14

REPORT_DIR = "reports"

# --- Canadian / no-FX-fee options ---
# Wealthsimple charges 1.5% to convert CAD<->USD on every US trade (CAD account).
# Canadian-listed stocks (.TO/.V) and CDRs (CAD-hedged US stocks on Cboe Canada) avoid it.
# US ticker -> Cboe Canada CDR ticker (from CIBC/BMO CDR announcements; check
# cboe.com/listings/ca/cdr for the full, current list and add more here).
CDR_MAP = {
    "ABT": "ABT", "AMGN": "AMGN", "AZO": "AZO", "SCHW": "SCHW", "FI": "FI",
    "GEV": "GEV", "GILD": "GILD", "KKR": "KKR", "MS": "MS", "NEE": "NEE",
    "PEP": "PEP", "SPGI": "SPGI", "TJX": "TJX", "UNP": "UNP", "WM": "WAST",
    "ABNB": "ABNB", "AMAT": "AMAT", "ANET": "ANET", "BX": "BX", "CMG": "CMGS",
    "MRK": "MRK", "OXY": "OXY", "ORCL": "ORAC", "PLTR": "PLTR", "WFC": "WFCS",
}

# --- Signals ---
# ENTRY SIGNAL: passes this many investors' rules, trend is up (not overheated),
# business isn't junk, and the market isn't risk-off.
ENTRY_MIN_PASSES = 4
ENTRY_MIN_BUFFETT = 10
