"""Holdings check: % below all-time / 52-week high, 1-year return, Cowen band position."""
import yfinance as yf, pandas as pd
T = ["VEQT.TO", "XEQT.TO", "VFV.TO", "XDIV.TO", "CCO.TO", "CGL-C.TO", "ZGLD.TO", "INFQ", "IMSR", "CASH.TO"]
for t in T:
    try:
        d = yf.download(t, period="max", interval="1d", auto_adjust=False, progress=False)
        c = d["Close"].squeeze().dropna()
        w = c.resample("W-FRI").last().dropna()
        sma, ema = w.rolling(20).mean().iloc[-1], w.ewm(span=21, adjust=False).mean().iloc[-1]
        p = c.iloc[-1]
        ath = c.max(); hi52 = c[c.index >= c.index[-1] - pd.Timedelta(days=365)].max()
        y1 = c[c.index <= c.index[-1] - pd.Timedelta(days=365)]
        r1 = (p / y1.iloc[-1] - 1) * 100 if len(y1) else float("nan")
        print(f"{t:9} {p:9.2f} | ATH {ath:9.2f} ({c.idxmax():%Y-%m-%d}) {((p/ath)-1)*100:6.1f}% | 52w-hi {((p/hi52)-1)*100:6.1f}% | 1y {r1:6.1f}% | band {((p/max(sma,ema))-1)*100:+.1f}% vs top, {((p/min(sma,ema))-1)*100:+.1f}% vs bottom")
    except Exception as e:
        print(t, "failed", e)
