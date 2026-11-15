import yfinance as yf, pandas as pd
for t, name in [("^SP500TR", "S&P 500 total return (USD)"), ("^GSPC", "S&P 500 price only, since 1928")]:
    c = yf.download(t, period="max", interval="1mo", auto_adjust=True, progress=False)["Close"].squeeze().dropna()
    r = (c / c.shift(24) - 1).dropna()
    neg = r[r < 0]
    print(f"\n{name}: {c.index[0]:%Y-%m} to {c.index[-1]:%Y-%m}")
    print(f"  2-year windows negative: {len(neg)}/{len(r)} = {len(neg)/len(r)*100:.0f}%  | worst 2-yr: {r.min()*100:.0f}% ending {r.idxmin():%Y-%m}")
    yrs = sorted({d.year for d in neg.index})
    print("  years with a negative 2-yr window ending in them:", yrs)
