"""Nov 19, 2026 test of the 3 signal fixes on live data (weekly-close rule, dollar, commodity gate)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scanner, config

print("== Market weather ==")
m = scanner.macro_weather()
for n in m["notes"]:
    print("  ", n)
print("   dollar_up:", m.get("dollar_up"), "| hiking:", m.get("hiking"), "| REGIME:", m["regime"])

print("\n== Commodity trends ==")
g = scanner.commodity_trends()

print("\n== Gate + trend on sample stocks ==")
test = ["BTO.TO", "LUG.TO", "KNT.TO", "NEM", "ERO.TO", "COP", "OVV", "EOG", "PEY.TO", "CCO.TO",
        "CTSH", "URBN", "VIRT", "ALSN", "NXPI"]
px = scanner.download_weekly(test)
for t in test:
    f = scanner.get_info(t)
    tr = scanner.cowan(px[t]) if t in px else {"trend": "no prices"}
    key = config.COMMODITY_GATE.get(f.get("industry"))
    gate = "-" if not key else ("BLOCKED: " + g[key]["name"] + " below trend" if key in g and not g[key]["up"] else "ok (" + key + " up)")
    last = px[t].index[-1].date() if t in px else "?"
    print(f"  {t:8} {str(f.get('industry'))[:32]:32} | {tr['trend']:34} | gate {gate} | last bar {last} in-progress={scanner.week_in_progress(px[t]) if t in px else '?'}")
