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

# Bitcoin-linked names also get crypto Reddit + crypto mood
CRYPTO_LINKED = ["MSTR", "COIN", "MARA", "RIOT", "HUT.TO", "BITF.TO"]
CRYPTO_SUBREDDITS = ["Bitcoin", "CryptoCurrency", "MSTR", "BitcoinMarkets"]

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


# ---- Legends (Nov 11, 2026: v2, expanded to 8; drop the ones that don't predict returns) ----
# v3 (Nov 20, 2026, Langley): O'Neil + Momentum merged into one 'Growth' legend (business growth,
# no buying-near-highs); Cowen also credits a 'DCA zone' (quality stock deep below its band);
# Buffett can't pass commodity producers. O'Neil and Momentum are still computed as info columns.
LEGENDS = ["cowan", "buffett", "lynch", "growth", "greenblatt", "piotroski", "graham"]
LEGEND_LABELS = {"cowan": "Cowan", "buffett": "Buffett", "lynch": "Lynch", "growth": "Growth",
                 "greenblatt": "Greenblatt", "piotroski": "Piotroski", "graham": "Graham",
                 "oneil": "O'Neil", "momentum": "Momentum"}
SCORING_VERSION = "v3"
DCA_ZONE_BELOW_BAND = -15   # % below the 20-week line
DCA_MIN_BUFFETT = 14        # only quality businesses (Buffett passes)
DCA_ZONE_POINTS = 14        # counts as Cowen agreeing (slow buying, not a lump sum)
PIOTROSKI_TOP_N = 250   # how many top candidates get the full-statement Piotroski check


# Fed (FOMC) rate-decision days (2nd day of each meeting). Source: federalreserve.gov calendar;
# 2027 dates are the Fed's tentative schedule. Add 2028 when the Fed publishes it (usually ~Aug/Sep).
FOMC_DATES = [
    "2026-12-09",
    "2027-01-27", "2027-03-17", "2027-04-28", "2027-06-09",
    "2027-07-28", "2027-09-15", "2027-10-27", "2027-12-08",
]


# Close watch (Nov 18, 2026): daily detail on gold, silver, Bitcoin and MSTR.
# name: Yahoo ticker. Shown in brief.md and written to reports/watch.csv.
CLOSE_WATCH = {
    "Bitcoin": "BTC-USD",
    "Gold (CGL.C/ZGLD)": "CGL-C.TO",
    "Gold (spot, GLD)": "GLD",
    "Silver (PSLV)": "PSLV.TO",
    "Silver (spot, SLV)": "SLV",
    "Wheaton (WPM)": "WPM.TO",
    "MSTR": "MSTR",
}
BIG_MOVE = {"BTC-USD": 5, "MSTR": 8}   # % daily move that counts as "big"; others 3%


# Commodity gate (Nov 19, 2026): miners/producers can't be picks while the commodity itself is
# below its trend line. Yahoo industry -> proxy ticker. Missing data = no gate.
COMMODITY_PROXY = {"Gold": "GLD", "Silver": "SLV", "Copper": "CPER", "Oil": "USO",
                   "Uranium": "U-UN.TO"}
COMMODITY_GATE = {
    "Gold": "GLD",
    "Other Precious Metals & Mining": "SLV",
    "Silver": "SLV",
    "Copper": "CPER",
    "Oil & Gas E&P": "USO",
    "Oil & Gas Integrated": "USO",
    "Oil & Gas Drilling": "USO",
    "Oil & Gas Equipment & Services": "USO",
    "Uranium": "U-UN.TO",
}
