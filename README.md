# TFSA Scanner

Every Saturday morning, GitHub runs this automatically. It scores about 750 stocks: the whole S&P 500, the TSX Composite, your holdings and your watchlist.

**Where to read it:** open `reports/latest.md` in the GitHub phone app or on github.com. It shows as a clean table. Older weeks are saved as `reports/scan-YYYY-MM-DD.md`.

## How stocks are scored (out of 100)

Five famous investors' rules, 20 points each:

| Investor | What it rewards |
|---|---|
| **Ben Cowen** | Trend: price vs the 20-week SMA / 21-week EMA "bull market support band". Just climbed back above it = 20, uptrend = 16, testing = 10, overheated (40%+ above) = 8, just fell below = 2, downtrend = 0 |
| **Warren Buffett** | P/E under 25, return on equity 15%+, low debt, 10%+ profit margin, positive free cash flow. Index ETFs get a pass |
| **Peter Lynch** | Growth at a reasonable price: P/E divided by growth (PEG) under 1 |
| **William O'Neil** | Earnings up 25%+, sales up 20%+, within 15% of its 52-week high, beating the S&P 500 over 6 months |
| **Joel Greenblatt** | Magic Formula: high return on capital + cheap price, ranked against every other stock (banks and utilities skipped) |

"Passes" = how many investors' rules a stock meets (14+ out of 20). Stocks that several legends would agree on rise to the top.

The top 25 picks and your holdings also get a **news + Reddit check** (Google News + r/stocks, r/CanadianInvestor, r/wallstreetbets and others).

The **market weather** (Fed rate, unemployment/Sahm rule, yield curve, Bitcoin trend) sets RISK-ON / NEUTRAL / RISK-OFF. In RISK-OFF, emerging/speculative picks get a warning tag.

**Verdicts:** CORE · WAIT FOR ENTRY · EMERGING · SPECULATIVE MOMENTUM · DON'T CHASE · AVOID FOR NOW · WATCH

## Change things

Edit `config.py` right on github.com (pencil icon) to update `HOLDINGS`, add to `WATCHLIST`, or adjust the rules. The next run picks it up.

To run a scan right now: **Actions** tab → **Weekly TFSA scan** → **Run workflow**.

## Notes

- Data: Yahoo Finance (via `yfinance`, free, unofficial, occasionally flaky), FRED, CoinGecko, Wikipedia (index member lists), Google News, Reddit.
- A full scan takes roughly 30-60 minutes on GitHub's free computers.
- Sentiment is a rough word count. Read the actual news before acting.
- Not backtested yet. Research tool only, never trades, not financial advice.
- TFSA: avoid frequent trading (CRA can treat it as business income); US dividends lose 15% to withholding.
