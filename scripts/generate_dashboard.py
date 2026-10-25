#!/usr/bin/env python3
"""Builds assets/dashboard.svg, a GitHub profile dashboard.

Standard library only. Reads public github.com pages, so no token is needed.
Env: GH_USER, DASH_OUT, DASH_TODAY (YYYY-MM-DD, optional).
"""
import os, re, sys, urllib.request
from collections import Counter
from datetime import date, timedelta
from html import escape

USER = os.environ.get("GH_USER", "Amr4924")
OUT = os.environ.get("DASH_OUT", "assets/dashboard.svg")
TODAY = date.fromisoformat(os.environ["DASH_TODAY"]) if os.environ.get("DASH_TODAY") else date.today()
YEARS = 5  # calendar years read for the all-time total and the longest streak


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (profile-dashboard)", "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


# ---------- fetch ----------
prof = get(f"https://github.com/{USER}")


def grab(pat):
    m = re.search(pat, prof, re.S)
    return m.group(1).strip() if m else None


name = grab(r'itemprop="name"[^>]*>\s*([^<]+)')
followers = grab(r'tab=followers[^>]*>.*?<span[^>]*>\s*([\d.,]+[kKmM]?)\s*</span>') or "0"
repo_ct = grab(r'data-tab-item="repositories"[^>]*>.*?<span[^>]*Counter[^>]*>\s*([\d,]+)')


def repos_page(p):
    html = get(f"https://github.com/{USER}?tab=repositories&type=source&page={p}")
    out = []
    for seg in html.split('itemprop="owns"')[1:]:
        lang = re.search(r'itemprop="programmingLanguage">([^<]+)<', seg)
        star = re.search(r'/stargazers">.*?</svg>\s*([\d,]+)\s*</a>', seg, re.S)
        out.append((lang.group(1).strip() if lang else None, int(star.group(1).replace(",", "")) if star else 0))
    return out


rows, page = [], 1
while page <= 10:
    chunk = repos_page(page)
    if not chunk:
        break
    rows += chunk
    page += 1
stars = sum(s for _, s in rows)
langs = Counter(l for l, _ in rows if l)
repo_total = int(repo_ct.replace(",", "")) if repo_ct else len(rows)


def year_counts(y):
    html = get(f"https://github.com/users/{USER}/contributions?from={y}-01-01&to={y}-12-31")
    tips = dict(re.findall(r'<tool-tip[^>]*\bfor="([^"]+)"[^>]*>\s*([^<]*?)\s*</tool-tip>', html))
    out = {}
    for tag in re.findall(r"<td\b[^>]*\bdata-date=[^>]*>", html):
        d = re.search(r'data-date="([\d-]+)"', tag).group(1)
        i = re.search(r'\bid="([^"]+)"', tag)
        m = re.match(r"([\d,]+)\s+contribution", tips.get(i.group(1), "")) if i else None
        out[d] = int(m.group(1).replace(",", "")) if m else 0
    return out


counts = {}
for y in range(TODAY.year - YEARS + 1, TODAY.year + 1):
    counts.update(year_counts(y))
counts = {d: c for d, c in counts.items() if d <= TODAY.isoformat()}
if not any(counts.values()):
    sys.exit("Could not read the contribution calendar; leaving the file unchanged.")

# ---------- numbers ----------
iso = lambda d: d.isoformat()
longest, run, start, prev = (0, None, None), 0, None, None
for d in sorted(counts):
    dd = date.fromisoformat(d)
    if counts[d] > 0:
        if run and prev and (dd - prev).days == 1:
            run += 1
        else:
            run, start = 1, dd
        prev = dd
        if run > longest[0]:
            longest = (run, start, dd)
    else:
        run, prev = 0, None

d = TODAY if counts.get(iso(TODAY), 0) > 0 else TODAY - timedelta(days=1)
cur_end, cur = d, 0
while counts.get(iso(d), 0) > 0:
    cur += 1
    d -= timedelta(days=1)
cur_start = d + timedelta(days=1)

total_all = sum(counts.values())
last_year = sum(c for k, c in counts.items() if date.fromisoformat(k) > TODAY - timedelta(days=365))
first = date.fromisoformat(min(k for k, c in counts.items() if c > 0))

# heatmap grid: 53 weeks, Sunday first, ending with the current week
sunday = TODAY - timedelta(days=(TODAY.weekday() + 1) % 7)
g0 = sunday - timedelta(weeks=52)
cells = []
for col in range(53):
    for row in range(7):
        dd = g0 + timedelta(days=col * 7 + row)
        if dd <= TODAY:
            cells.append((col, row, counts.get(iso(dd), 0)))
nz = sorted(c for *_, c in cells if c)


def level(c):
    if not c:
        return 0
    q = lambda f: nz[min(len(nz) - 1, int(len(nz) * f))]
    return 1 if c <= q(.25) else 2 if c <= q(.5) else 3 if c <= q(.75) else 4


# ---------- draw ----------
W, H, M = 860, 540, 34
BG, LINE, TXT, MUTED = "#0D1117", "#21262D", "#E6EDF3", "#8B949E"
FOAM, ROSE = "#9CCFD8", "#EBBCBA"
LV = ["#161B22", "#45204F", "#6E2A86", "#9C27B0", "#D17FE6"]
LC = {"Dart": "#00B4AB", "JavaScript": "#F1E05A", "TypeScript": "#3178C6", "HTML": "#E34C26", "CSS": "#563D7C",
      "C++": "#F34B7D", "C": "#8A8A8A", "Python": "#3572A5", "Java": "#B07219", "Kotlin": "#A97BFF",
      "Swift": "#F05138", "Shell": "#89E051", "Astro": "#FF5A03", "PHP": "#8892BF", "C#": "#178600"}
FALL = ["#9CCFD8", "#EBBCBA", "#C4A7E7", "#F6C177", "#EB6F92", "#31748F"]
FONT = "-apple-system,'Segoe UI',Ubuntu,Roboto,'Helvetica Neue',Arial,sans-serif"
fmt = lambda v: f"{v:,}" if isinstance(v, int) else str(v)
short = lambda d: f"{d.strftime('%b')} {d.day}"


def span(a, b):
    if a == b:
        return short(a) + ("" if a.year == TODAY.year else f", {a.year}")
    if a.year == b.year:
        return f"{short(a)} – {short(b)}" + ("" if b.year == TODAY.year else f", {b.year}")
    return f"{short(a)}, {a.year} – {short(b)}, {b.year}"


o = []


def T(x, y, s, size=13, fill=MUTED, w=400, anchor="start"):
    o.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{s}</text>')


def hl(y):
    o.append(f'<path d="M{M} {y}.5H{W - M}" stroke="{LINE}" shape-rendering="crispEdges"/>')


def vl(x, y1, y2):
    o.append(f'<path d="M{x}.5 {y1}V{y2}" stroke="{LINE}" shape-rendering="crispEdges"/>')


o.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
         f'font-family="{FONT}" role="img" aria-label="GitHub dashboard for {escape(USER)}">')
o.append('<style>@keyframes p{from{opacity:0}to{opacity:1}}.h{animation:p .5s ease-out backwards}'
         '@media(prefers-reduced-motion:reduce){.h{animation:none}}</style>')
o.append(f'<rect width="{W}" height="{H}" rx="16" fill="{BG}"/>'
         f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="15.5" fill="none" stroke="#30363D"/>')

# header
T(M, 56, "@" + escape(USER), 30, TXT, 800)
if name:
    T(M, 80, escape(name), 14)
T(W - M, 56, f"github.com/{escape(USER)}", 14, FOAM, 600, "end")
hl(100)

# stat strip
stats = [(last_year, "Contributions, past year"), (stars, "Stars"), (repo_total, "Repositories"), (followers, "Followers")]
for i, (v, label) in enumerate(stats):
    x = M + i * 198 + (22 if i else 0)
    if i:
        vl(M + i * 198, 118, 178)
    T(x, 148, fmt(v), 32, TXT, 800)
    T(x, 170, label, 13)
hl(196)

# heatmap (the one animated element: columns reveal left to right)
T(M, 226, "Contribution activity", 15, TXT, 600)
x0, y0, P = M, 264, 15
mon = lambda c: (g0 + timedelta(days=c * 7)).month
chg = [c for c in range(1, 53) if mon(c) != mon(c - 1)]
for c in ([0] if not chg or chg[0] >= 3 else []) + chg:
    T(x0 + c * P, 254, (g0 + timedelta(days=c * 7)).strftime("%b"), 11)
bycol = {}
for col, row, c in cells:
    bycol.setdefault(col, []).append(
        f'<rect x="{x0 + col * P}" y="{y0 + row * P}" width="12" height="12" rx="3" fill="{LV[level(c)]}"/>')
for col in sorted(bycol):
    o.append(f'<g class="h" style="animation-delay:{col * 0.022:.2f}s">{"".join(bycol[col])}</g>')
T(W - M, 397, "More", 11, MUTED, 400, "end")
for i in range(5):
    o.append(f'<rect x="{W - M - 34 - 72 + i * 15}" y="386" width="12" height="12" rx="3" fill="{LV[i]}"/>')
T(W - M - 34 - 72 - 8, 397, "Less", 11, MUTED, 400, "end")
hl(414)

# languages, by repository
T(M, 440, "Languages by repository", 15, TXT, 600)
top = langs.most_common(6)
if len(langs) > 6:
    top = langs.most_common(5) + [("Other", sum(langs.values()) - sum(n for _, n in langs.most_common(5)))]
tot = sum(n for _, n in top) or 1
colors = [LC.get(n, FALL[i % len(FALL)]) if n != "Other" else "#6E7681" for i, (n, _) in enumerate(top)]
o.append(f'<clipPath id="lb"><rect x="{M}" y="452" width="400" height="10" rx="5"/></clipPath><g clip-path="url(#lb)">')
cx = float(M)
for (n, k), col in zip(top, colors):
    w = 400 * k / tot
    o.append(f'<rect x="{cx:.1f}" y="452" width="{w:.1f}" height="10" fill="{col}"/>')
    cx += w
o.append("</g>")
for i, ((n, k), col) in enumerate(zip(top, colors)):
    x, y = M + (i % 3) * 134, 488 + (i // 3) * 20
    o.append(f'<circle cx="{x + 4}" cy="{y - 4}" r="4" fill="{col}"/>')
    T(x + 14, y, f'{escape(n)} <tspan fill="{MUTED}">{round(100 * k / tot)}%</tspan>', 13, TXT)

# streak
vl(452, 428, 518)
T(470, 440, "Streak", 15, TXT, 600)
blocks = [
    (f'{cur}<tspan font-size="12" font-weight="400" fill="{MUTED}" dx="5">{"day" if cur == 1 else "days"}</tspan>', ROSE, "Current streak",
     span(cur_start, cur_end) if cur else "No active streak"),
    (f'{longest[0]}<tspan font-size="12" font-weight="400" fill="{MUTED}" dx="5">{"day" if longest[0] == 1 else "days"}</tspan>', TXT, "Longest streak",
     span(longest[1], longest[2])),
    (fmt(total_all), TXT, "Contributions", f"since {first.strftime('%b %Y')}"),
]
for i, (v, col, label, sub) in enumerate(blocks):
    x = 470 + i * 122
    T(x, 478, v, 30, col, 800)
    T(x, 498, label, 12)
    T(x, 515, sub, 11, "#6E7681")

o.append("</svg>")
os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(o))
print(f"wrote {OUT}: {len(counts)} days, {total_all} contributions, {len(rows)} source repos, "
      f"stars={stars}, followers={followers}, repos={repo_total}, streak={cur}/{longest[0]}, langs={dict(langs)}")
