"""One-off research: VEQT vs VFV-style returns since 2000 / 2010 / 2020, in CAD, dividends reinvested.
VFV proxy  = S&P 500 total return (^SP500TR) converted to CAD.
VEQT proxy = 30% Canada (XIU.TO, adj close) + 43% US total market (VTSMX) + 27% international incl.
             emerging (VGTSX), US funds converted to CAD, rebalanced monthly.
Since 2020 the real funds (VFV.TO, VEQT.TO) are shown too."""
import pandas as pd, yfinance as yf, numpy as np

def monthly(t):
    d = yf.download(t, start="1999-11-01", interval="1mo", auto_adjust=True, progress=False)["Close"]
    s = d.iloc[:, 0] if isinstance(d, pd.DataFrame) else d
    s.index = s.index.to_period("M")
    return s.dropna()

fx = monthly("CAD=X")
# Yahoo's USD/CAD starts Oct 2003; fill earlier months from the Fed's H.10 series via DBnomics
import requests
for sid in ["FED/H10/RXI_N.M.CA", "FED/G5/RXI_N.M.CA"]:
    try:
        j = requests.get(f"https://api.db.nomics.world/v22/series/{sid}?observations=1", timeout=30).json()
        d = j["series"]["docs"][0]
        old = pd.Series(pd.to_numeric(d["value"], errors="coerce"), index=pd.PeriodIndex(d["period"], freq="M")).dropna()
        print("DBnomics", sid, old.index[0], old.index[-1])
        fx = pd.concat([old[old.index < fx.index[0]], fx]).sort_index()
        break
    except Exception as e:
        print("DBnomics failed", sid, e)
print("FX first month:", fx.index[0])
spx, us, intl, ca = monthly("^SP500TR"), monthly("VTSMX"), monthly("VGTSX"), monthly("XIU.TO")
for n, s in [("SP500TR", spx), ("VTSMX", us), ("VGTSX", intl), ("XIU", ca)]:
    print(n, "first", s.index[0], "last", s.index[-1])
df = pd.concat({"fx": fx, "spx": spx, "us": us, "intl": intl, "ca": ca}, axis=1).dropna()
r = pd.DataFrame({
    "vfv": (df.spx * df.fx).pct_change(),
    "veqt": 0.30 * df.ca.pct_change() + 0.43 * (df.us * df.fx).pct_change() + 0.27 * (df.intl * df.fx).pct_change(),
}).dropna()
real = pd.concat({"VFV.TO": monthly("VFV.TO"), "VEQT.TO": monthly("VEQT.TO")}, axis=1).pct_change()

def stats(x):
    g = (1 + x).cumprod()
    yrs = len(x) / 12
    return f"$10k -> ${10000 * g.iloc[-1]:,.0f} | {((g.iloc[-1]) ** (1 / yrs) - 1) * 100:.1f}%/yr | worst drop {((g / g.cummax()) - 1).min() * 100:.0f}%"

for start in ["2000-01", "2010-01", "2020-01"]:
    w = r[r.index >= start]
    print(f"\nSince {start} ({w.index[0]} to {w.index[-1]}, {len(w)/12:.1f} yrs)")
    print("  VFV-style (S&P 500, CAD):", stats(w.vfv))
    print("  VEQT-style (global mix, CAD):", stats(w.veqt))
    if start == "2020-01":
        rr = real[real.index >= start].dropna()
        print("  REAL VFV.TO :", stats(rr["VFV.TO"]))
        print("  REAL VEQT.TO:", stats(rr["VEQT.TO"]))
w = r[(r.index >= "2000-01") & (r.index <= "2009-12")]
print("\nLost decade 2000-2009: VFV-style", stats(w.vfv), "| VEQT-style", stats(w.veqt))
