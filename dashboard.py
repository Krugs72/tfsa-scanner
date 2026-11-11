"""Builds reports/dashboard.html: a clean phone-first dashboard from the scan."""
import datetime as dt
import json
import math

import config


def _num(x):
    try:
        f = float(x)
        return None if math.isnan(f) else f
    except Exception:
        return None


def _row(r):
    inv = config.LEGENDS
    return {
        "t": r["ticker"], "n": str(r["name"])[:34], "p": _num(r["price"]),
        "score": int(r["total"]), "passes": int(r["passes"]),
        "raw": int(r.get("passes_raw", r["passes"])), "avail": int(r.get("legends_avail", 5)),
        "checks": {k: (None if _num(r.get(k)) is None else bool(r[k] >= config.PASS_MARK)) for k in inv},
        "flags": r["red_flags"] if isinstance(r.get("red_flags"), str) else "",
        "signal": r["signal"] if isinstance(r["signal"], str) else "",
        "cur": r["currency"],
        "cdr": config.CDR_MAP.get(r["ticker"], ""),
        "trend": r["trend"], "band": _num(r["pct_vs_band"]),
        "rg": _num(r.get("rev_growth")), "eg": _num(r.get("eps_growth")),
        "pe": _num(r.get("pe")), "r6": _num(r.get("ret_26w")),
        "g": int(r["growth_score"]) if _num(r.get("growth_score")) is not None else None,
        "cyc": r.get("sector") in ("Basic Materials", "Energy"),
        "news": r["headline"] if isinstance(r.get("headline"), str) else "",
    }


def write_dashboard(df, macro, path):
    held = set(config.HOLDINGS)
    ok = (~df.ticker.isin(held)) & df.is_stock.astype(bool) & \
         (~df.trend.astype(str).str.contains("Overheated")) & (df.buffett >= 6) & \
         df.get("pick_ok", True).astype(bool)
    consensus = df[ok & (df.passes >= 4) & (df.cowan >= 10)] \
        .sort_values(["passes", "total"], ascending=False) \
        .drop_duplicates("name")   # e.g. FOX and FOXA are the same company
    # max 3 per sector so one industry (e.g. insurers) can't take over the list
    consensus = consensus[consensus.groupby(consensus.sector.fillna("?")).cumcount() < 3].head(12)
    growth = df[ok & (df.cowan >= 10)].copy()
    growth = growth[growth.rev_growth.astype(float).fillna(0) >= 0.10]
    growth = growth[~growth.ticker.isin(consensus.ticker.head(6))] \
        .sort_values("growth_score", ascending=False).drop_duplicates("name").head(8)
    other = df[df.ticker.isin(config.WATCHLIST) & ~df.ticker.isin(held)] \
        .sort_values("cowan", ascending=False).head(6)
    hold = df[df.ticker.isin(held)]
    data = {
        "date": f"{dt.date.today():%a %b %d, %Y}",
        "regime": macro.get("regime", "?"),
        "notes": macro.get("notes", []),
        "scanned": int(len(df)),
        "consensus": [_row(r) for _, r in consensus.iterrows()],
        "growth": [_row(r) for _, r in growth.iterrows()],
        "other": [_row(r) for _, r in other.iterrows()],
        "hold": [_row(r) for _, r in hold.iterrows()],
        "counts": {str(k): int(v) for k, v in df.passes.value_counts().sort_index().items()},
    }
    html = TEMPLATE.replace("__DATA__", json.dumps(data).replace("</", "<\\/"))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TFSA Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#14171f;--mute:#6b7280;--line:#e6e8ec;--good:#0f9d58;--warn:#d97706;--bad:#dc2626;--chip:#eef1f5;--accent:#2563eb}
@media (prefers-color-scheme:dark){:root{--bg:#0d0f13;--card:#171a21;--ink:#eef0f4;--mute:#9aa3b2;--line:#262b35;--chip:#222733;--accent:#60a5fa}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 Inter,system-ui,sans-serif}
.wrap{max-width:760px;margin:0 auto;padding:16px 14px 40px}
h1{font-size:22px;margin:4px 0 2px}h2{font-size:16px;margin:26px 0 10px;display:flex;align-items:center;gap:8px}
.sub{color:var(--mute);font-size:13px}
.weather{margin-top:12px;padding:12px 14px;border-radius:14px;background:var(--card);border:1px solid var(--line)}
.regime{font-weight:700;font-size:15px}.regime.on{color:var(--good)}.regime.off{color:var(--bad)}.regime.mid{color:var(--warn)}
.weather ul{margin:6px 0 0;padding-left:18px;color:var(--mute);font-size:13px}
.tabs{display:flex;gap:6px;margin:6px 0 10px}.tab{border:1px solid var(--line);background:var(--card);color:var(--ink);padding:6px 12px;border-radius:999px;font:inherit;font-size:13px;cursor:pointer}
.tab.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 14px;margin-bottom:10px}
.top{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
.tk{font-weight:700;font-size:16px}.nm{color:var(--mute);font-size:13px}
.score{text-align:right}.big{font-size:20px;font-weight:700}.small{font-size:11px;color:var(--mute)}
.badges{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 6px}
.b{font-size:11px;font-weight:600;padding:3px 8px;border-radius:999px;background:var(--chip)}
.b.sig{background:#dcfce7;color:#166534}.b.strong{background:#166534;color:#fff}.b.fx{background:#fef3c7;color:#92400e}.b.cyc{background:#ffedd5;color:#9a3412}.b.ca{background:#e0e7ff;color:#3730a3}
@media (prefers-color-scheme:dark){.b.sig{background:#14532d;color:#bbf7d0}.b.fx{background:#451a03;color:#fde68a}.b.cyc{background:#431407;color:#fed7aa}.b.ca{background:#1e1b4b;color:#c7d2fe}}
.legends{display:flex;gap:4px;margin:4px 0 8px;flex-wrap:wrap}
.flag{color:#b45309;font-size:12px;margin:2px 0 6px}
.lg{font-size:11px;padding:2px 7px;border-radius:6px;border:1px solid var(--line);color:var(--mute)}
.lg.y{border-color:var(--good);color:var(--good);font-weight:600}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:4px}
.st{background:var(--chip);border-radius:10px;padding:6px 8px}.st b{display:block;font-size:14px}.st span{font-size:10px;color:var(--mute);text-transform:uppercase;letter-spacing:.03em}
.pos{color:var(--good)}.neg{color:var(--bad)}
.why{margin:8px 0 0;padding-left:18px;font-size:13px}
.news{font-size:12px;color:var(--mute);margin-top:6px}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;font-size:13px}
td,th{padding:9px 10px;border-bottom:1px solid var(--line);text-align:left}th{font-size:11px;color:var(--mute);font-weight:600;text-transform:uppercase}
tr:last-child td{border-bottom:0}.flag{font-weight:600;font-size:12px}
.empty{color:var(--mute);font-size:13px;padding:6px 2px}
.foot{margin-top:28px;font-size:12px;color:var(--mute)}
details summary{cursor:pointer;color:var(--accent)}
</style></head><body><div class="wrap" id="app"></div>
<script>
const D=__DATA__;
const L={cowan:"Cowan",buffett:"Buffett",lynch:"Lynch",oneil:"O'Neil",greenblatt:"Greenblatt",piotroski:"Piotroski",graham:"Graham",momentum:"Momentum"};
const el=(t,c,h)=>{const e=document.createElement(t);if(c)e.className=c;if(h!=null)e.textContent=h;return e};
const pct=x=>x==null?"–":(x>=0?"+":"")+Math.round(x*100)+"%";
const money=x=>x==null?"–":"$"+x.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
function why(r){const w=[];
 if(r.trend.includes("RECLAIMED"))w.push("Just broke back above its trend line (Cowan's buy zone)");
 else if(r.trend==="Uptrend")w.push(`In an uptrend${r.r6!=null?`, ${r.r6>=0?"+":""}${Math.round(r.r6)}% in 6 months`:""}`);
 if(r.rg!=null&&r.rg>=0.15)w.push(`Sales growing fast (${pct(r.rg)} vs last year)`);
 if(r.eg!=null&&r.eg>5)w.push("Earnings jumped 5x+, likely off a low base, check it's not one-off");
 else if(r.eg!=null&&r.eg>=0.25)w.push(`Earnings up ${pct(r.eg)}`);
 if(r.pe!=null&&r.pe>0&&r.pe<=20)w.push(`Cheap for what it earns (P/E ${Math.round(r.pe)})`);
 if(r.cyc)w.push("Rides metal/oil prices: great when they're high, painful when they drop");
 return w.slice(0,4)}
function card(r){const c=el("div","card");const top=el("div","top");
 const l=el("div");l.append(el("div","tk",r.t),el("div","nm",r.n));
 const s=el("div","score");s.append(el("div","big",r.score),el("div","small",`/100 · ${money(r.p)}`));top.append(l,s);c.append(top);
 const bd=el("div","badges");
 if(r.signal.includes("STRONG"))bd.append(el("span","b strong","🔔 STRONG ENTRY"));else if(r.signal.includes("ENTRY"))bd.append(el("span","b sig","🔔 Entry signal"));
 bd.append(el("span","b",`${r.raw}/${r.avail} legends agree`));
 if(r.cur==="CAD")bd.append(el("span","b ca","🇨🇦 No FX fee"));else if(r.cur==="CDR")bd.append(el("span","b ca",`🇨🇦 Buy as ${r.cdr} (CDR)`));else bd.append(el("span","b fx","💱 1.5% FX fee"));
 if(r.cyc)bd.append(el("span","b cyc","⚠️ Commodity"));c.append(bd);
 const lg=el("div","legends");for(const k in L)lg.append(el("span","lg"+(r.checks[k]?" y":""),(r.checks[k]?"✓ ":"")+L[k]+(r.checks[k]===null?" (no data)":"")));c.append(lg);if(r.flags)c.append(el("p","flag","⚠️ "+r.flags));
 const st=el("div","stats");[["Sales",pct(r.rg),r.rg],["Earnings",r.eg>5?"5x+":pct(r.eg),r.eg],["P/E",r.pe?Math.round(r.pe):"–",null],["vs line",r.band==null?"–":(r.band>=0?"+":"")+Math.round(r.band)+"%",r.band]]
 .forEach(([k,v,n])=>{const d=el("div","st");const b=el("b",n==null?"":(n>=0?"pos":"neg"),v);d.append(b,el("span",null,k));st.append(d)});c.append(st);
 const w=why(r);if(w.length){const u=el("ul","why");w.forEach(x=>u.append(el("li",null,x)));c.append(u)}
 if(r.news)c.append(el("div","news","📰 "+r.news));return c}
function section(title,rows,withTabs){const app=document.getElementById("app");app.append(el("h2",null,title));
 const box=el("div");let mode="all";
 const draw=()=>{box.replaceChildren();const f=rows.filter(r=>mode==="all"||(mode==="ca"?r.cur!=="USD":r.cur==="USD"));
  if(!f.length)box.append(el("div","empty","Nothing qualifies today."));f.forEach(r=>box.append(card(r)))};
 if(withTabs){const t=el("div","tabs");[["all","All"],["ca","🇨🇦 Canada (no fee)"],["us","🇺🇸 US"]].forEach(([k,n])=>{const b=el("button","tab"+(k==="all"?" on":""),n);
  b.onclick=()=>{mode=k;t.querySelectorAll(".tab").forEach(x=>x.classList.remove("on"));b.classList.add("on");draw()};t.append(b)});app.append(t)}
 app.append(box);draw()}
const app=document.getElementById("app");
app.append(el("h1",null,"📈 TFSA Dashboard"),el("div","sub",`${D.date} · ${D.scanned} stocks scanned`));
const w=el("div","weather");const rg=D.regime.includes("ON")?"on":D.regime.includes("OFF")?"off":"mid";
w.append(el("div","regime "+rg,"Market: "+D.regime));const ul=el("ul");D.notes.forEach(n=>ul.append(el("li",null,n)));w.append(ul);app.append(w);
section("⭐ Top picks: most legends agree",D.consensus,true);
section("🚀 Fast growers (long runway)",D.growth,true);
app.append(el("h2",null,"🌐 Metals, crypto & themes"));
const t1=el("table");t1.innerHTML="<tr><th>Ticker</th><th>Price</th><th>Trend</th></tr>";
D.other.forEach(r=>{const tr=el("tr");tr.append(el("td",null,r.t),el("td",null,money(r.p)),el("td",null,`${r.trend} (${r.band>=0?"+":""}${Math.round(r.band||0)}%)`));t1.append(tr)});app.append(t1);
app.append(el("h2",null,"📌 Your holdings"));
const t2=el("table");t2.innerHTML="<tr><th>Holding</th><th>Price</th><th>Trend</th><th>Flag</th></tr>";
D.hold.forEach(r=>{const tr=el("tr");const f=r.signal?r.signal.split(" - ")[0]:"OK";const fe=el("td","flag",f);fe.style.color=f.includes("EXIT")?"var(--bad)":f.includes("TRIM")?"var(--warn)":f.includes("ADD")?"var(--good)":"var(--mute)";
 tr.append(el("td",null,r.t),el("td",null,money(r.p)),el("td",null,`${r.trend} (${r.band>=0?"+":""}${Math.round(r.band||0)}%)`),fe);t2.append(tr)});app.append(t2);
const ft=el("div","foot");const det=el("details");det.append(el("summary",null,"How the scores work"));
det.append(el("p",null,"8 legends, each worth 20 points (scaled to 100). A stock 'agrees' with a legend at 14+/20. Cowan = trend (above his 20-week line). Buffett = profitable, low debt, fair price. Lynch = growth at a reasonable price (uses next year's expected growth, so one-off jumps don't count). O'Neil = fast-rising earnings near highs. Greenblatt = high returns on capital + cheap. Piotroski = 9 checks that the business is really getting stronger (profits backed by cash, no new shares, less debt). Graham = cheap on earnings and assets with a strong balance sheet. Momentum = biggest 12-month winners (skipping the last month). No data for a legend = left out, not a fail. Red flags (one-off earnings, acquisition-driven sales, new shares, analysts' target below price, a crash, tiny/thinly traded) cost 5 points each; serious ones keep a stock out of the picks. We track how each legend's picks perform and drop the ones that don't help."));
det.append(el("p",null,"Spread today: "+Object.entries(D.counts).map(([k,v])=>`${k}/5: ${v}`).join(" · ")));
ft.append(det,el("p",null,"Research tool only, not financial advice. Check the news before acting, and keep speculative bets small."));app.append(ft);
</script></body></html>"""
