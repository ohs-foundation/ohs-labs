#!/usr/bin/env python3
"""Builds the OHS Labs site from experiments/*.md into dist/.

Usage:
  python build.py            # build into dist/
  python build.py --check    # validate the experiments only

Each experiment is one markdown file with YAML front matter. See
experiments/_template.md for every field.
"""

import datetime
import html
import json
import pathlib
import random
import re
import shutil
import sys

import markdown
import yaml

ROOT = pathlib.Path(__file__).resolve().parent
EXPERIMENTS = ROOT / "experiments"
ASSETS = ROOT / "assets"
TEMPLATE = ROOT / "templates" / "index.html"
DIST = ROOT / "dist"
REPO_URL = "https://github.com/ohs-foundation/ohs-labs"

# Stage id, label, what it means. The order is the lifecycle order.
STAGES = [
    ("proposal", "Proposal", "An idea we want to run. Looking for owners, data or a deployment to try it in."),
    ("percolating", "Percolating", "Work in progress. A harness exists and early results are coming in."),
    ("published", "Published", "Results, code and write-up are public, so anyone can rerun them."),
    ("graduated", "Graduated", "It worked, and it now lives in an OHS project or pillar."),
]
STAGE_IDS = [s[0] for s in STAGES]
STAGE_LABEL = {s[0]: s[1] for s in STAGES}
# Cards show the most mature work first.
STAGE_RANK = {"graduated": 0, "published": 1, "percolating": 2, "proposal": 3}
PATTERNS = {"bars", "dots", "tiles"}
CHART_TYPES = {"grouped-bars", "columns", "race"}

MD_EXT = ["extra", "sane_lists"]


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def md_inline(text):
    out = markdown.markdown(str(text or ""), extensions=MD_EXT)
    return re.sub(r"^<p>(.*)</p>$", r"\1", out.strip(), flags=re.S)


def add_target_blank(h):
    return re.sub(r'<a href="(https?://[^"]+)"', r'<a href="\1" target="_blank" rel="noopener"', h)


# ---------------------------------------------------------------- loading


def load(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.S)
    if not m:
        raise ValueError("missing YAML front matter between --- lines")
    meta = yaml.safe_load(m.group(1)) or {}
    meta["body"] = m.group(2)
    meta.setdefault("slug", path.stem)
    return meta


def validate(e, path):
    errs = []
    for f in ("title", "stage", "summary"):
        if not e.get(f):
            errs.append(f"'{f}' is required")
    if e.get("stage") and e["stage"] not in STAGE_IDS:
        errs.append(f"stage '{e['stage']}' must be one of: {', '.join(STAGE_IDS)}")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(e.get("slug", ""))):
        errs.append("slug (file name) may use only a-z, 0-9 and -")
    cover = e.get("cover") or {}
    if cover.get("pattern") and cover["pattern"] not in PATTERNS:
        errs.append(f"cover.pattern must be one of: {', '.join(sorted(PATTERNS))}")
    if cover.get("image") and not (ROOT / cover["image"]).exists():
        errs.append(f"cover.image {cover['image']} not found")
    for link in e.get("links") or []:
        if not link.get("label") or not link.get("url"):
            errs.append("every link needs a label and a url")
    charts = {c.get("id"): c for c in e.get("charts") or []}
    for c in charts.values():
        if c.get("type") not in CHART_TYPES:
            errs.append(f"chart {c.get('id')}: type must be one of {', '.join(sorted(CHART_TYPES))}")
        if c.get("type") == "race":
            src = charts.get(c.get("from"))
            if not src:
                errs.append(f"chart {c.get('id')}: from: must name a grouped-bars chart")
            elif c.get("group") not in src.get("groups", []):
                errs.append(f"chart {c.get('id')}: group {c.get('group')} is not in {src['id']}")
    for ref in re.findall(r"\{\{chart:([\w-]+)\}\}", e["body"]):
        if ref not in charts:
            errs.append(f"body uses {{{{chart:{ref}}}}} but no chart has id '{ref}'")
    return [f"{path.name}: {x}" for x in errs]


# ---------------------------------------------------------------- rendering


def art_svg(seed, a, b, kind, cls="bg"):
    """Generative cover art: brand gradient plus a light pattern."""
    rnd = random.Random(seed).random
    shapes = []
    if kind == "bars":
        for i in range(16):
            h = 30 + rnd() * 120
            shapes.append(f'<rect x="{20 + i * 26}" y="{220 - h:.0f}" width="16" height="{h:.0f}" rx="5" fill="#fff" opacity="{0.08 + rnd() * 0.22:.2f}"/>')
    elif kind == "dots":
        for y in range(8):
            for x in range(16):
                o = rnd()
                if o > 0.35:
                    shapes.append(f'<circle cx="{20 + x * 28}" cy="{20 + y * 28}" r="{3 + o * 6:.1f}" fill="#fff" opacity="{o * 0.35:.2f}"/>')
    else:
        for _ in range(9):
            s = 30 + rnd() * 70
            shapes.append(f'<rect x="{rnd() * 420:.0f}" y="{rnd() * 200:.0f}" width="{s:.0f}" height="{s:.0f}" rx="{s * 0.29:.0f}" fill="#fff" opacity="{0.06 + rnd() * 0.18:.2f}" transform="rotate({rnd() * 30 - 15:.0f})"/>')
    gid = f"g{seed}"
    return (
        f'<svg viewBox="0 0 460 240" preserveAspectRatio="xMidYMid slice" class="{cls}" aria-hidden="true">'
        f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{esc(a)}"/><stop offset="1" stop-color="{esc(b)}"/></linearGradient>'
        f'<linearGradient id="v{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset=".45" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".35"/></linearGradient></defs>'
        f'<rect width="460" height="240" fill="url(#{gid})"/>{"".join(shapes)}<rect width="460" height="240" fill="url(#v{gid})"/></svg>'
    )


def cover_html(e, seed):
    c = e.get("cover") or {}
    out = art_svg(seed, c.get("from", "#07585C"), c.get("to", "#4F3F83"), c.get("pattern", "tiles"))
    if c.get("image"):
        out += f'<img class="cover" src="{esc(c["image"])}" alt="" loading="lazy"/>'
    return out


def byline(e):
    if e.get("byline"):
        return e["byline"]
    parts = []
    if e.get("authors"):
        names = list(e["authors"])
        parts.append(names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1])
    if e.get("date"):
        d = e["date"]
        if isinstance(d, str):
            d = datetime.date.fromisoformat(d)
        parts.append(f"{d:%B} {d.day}, {d.year}")
    return " · ".join(parts)


def kpis_html(e):
    items = e.get("kpis") or []
    if not items:
        return ""
    cells = "".join(f'<div class="kpi"><b>{esc(k["value"])}</b><span>{md_inline(k.get("label", ""))}</span></div>' for k in items[:3])
    return f'<div class="kpis">{cells}</div>'


def video_html(url):
    if not url:
        return ""
    m = re.search(r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([\w-]{6,})", url)
    if m:
        return f'<div class="video"><iframe src="https://www.youtube-nocookie.com/embed/{m.group(1)}" title="Video" allow="accelerometer; encrypted-media; picture-in-picture" allowfullscreen loading="lazy"></iframe></div>'
    m = re.search(r"vimeo\.com/(\d+)", url)
    if m:
        return f'<div class="video"><iframe src="https://player.vimeo.com/video/{m.group(1)}" title="Video" allow="fullscreen; picture-in-picture" allowfullscreen loading="lazy"></iframe></div>'
    return f'<div class="video"><video controls preload="metadata" src="{esc(url)}"></video></div>'


def body_html(e):
    """Splits the body at '## Eyebrow | Heading' lines into white blocks."""
    chunks = re.split(r"(?m)^## +(.+)$", e["body"])
    out = []

    def render(md_text):
        h = markdown.markdown(md_text, extensions=MD_EXT)
        h = re.sub(r"<p>\s*\{\{kpis\}\}\s*</p>", lambda _: kpis_html(e), h)
        h = re.sub(r"<p>\s*\{\{chart:([\w-]+)\}\}\s*</p>", r'<div class="chart" data-chart="\1"></div>', h)
        return add_target_blank(h)

    pre = chunks[0].strip()
    if pre:
        out.append(render(pre))
    for i in range(1, len(chunks), 2):
        heading, text = chunks[i].strip(), chunks[i + 1]
        eyebrow, _, title = heading.partition("|")
        if not title:
            eyebrow, title = "", eyebrow
        out.append(
            '<div class="block">'
            + (f'<div class="eyebrow">{esc(eyebrow.strip())}</div>' if eyebrow.strip() else "")
            + f"<h3>{md_inline(title.strip())}</h3>{render(text)}</div>"
        )
    return "\n".join(out)


def card_html(e, seed):
    stat = e.get("stat") or {"value": STAGE_LABEL[e["stage"]], "label": "help shape it" if e["stage"] == "proposal" else ""}
    tags = "".join(f'<span class="tag">{esc(t)}</span>' for t in e.get("tags") or [])
    cta = "See the proposal" if e["stage"] == "proposal" else "See what we did"
    return f"""      <a class="card{' featured' if e.get('featured') else ''}" href="#/{e['slug']}" data-id="{e['slug']}" data-s="{e['stage']}">
        <div class="card-art">{cover_html(e, seed)}<div class="stat"><b>{esc(stat.get('value'))}</b><span>{esc(stat.get('label', ''))}</span></div></div>
        <div class="card-body">
          <div class="card-meta"><span class="badge st-{e['stage']}">{STAGE_LABEL[e['stage']]}</span><span class="mono" style="font-size:11px;color:var(--muted)">OHS Labs</span></div>
          <h3>{esc(e['title'])}</h3>
          <p>{esc(e['summary'])}</p>
          <div class="tags">{tags}</div>
          <div class="card-cta">{cta} <span class="arr">→</span></div>
        </div>
      </a>"""


def chart_data(c):
    c = dict(c)
    if c.get("note"):
        c["note"] = add_target_blank(md_inline(c["note"]))
    return c


# ---------------------------------------------------------------- main


def main(argv):
    files = sorted(p for p in EXPERIMENTS.glob("*.md") if not p.name.startswith("_"))
    exps, errors = [], []
    for p in files:
        try:
            e = load(p)
        except Exception as ex:  # report every broken file, not just the first
            errors.append(f"{p.name}: {ex}")
            continue
        errors += validate(e, p)
        exps.append(e)
    slugs = [e["slug"] for e in exps]
    for s in {s for s in slugs if slugs.count(s) > 1}:
        errors.append(f"slug '{s}' is used twice")
    if errors:
        print("Build failed:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1
    print(f"{len(exps)} experiments OK")
    if "--check" in argv:
        return 0

    exps.sort(key=lambda e: (not e.get("featured"), STAGE_RANK[e["stage"]], e.get("order", 100), e["title"]))
    counts = {s: sum(e["stage"] == s for e in exps) for s in STAGE_IDS}

    filters = ['        <button class="chip active" data-f="all">All<span class="count">%d</span></button>' % len(exps)]
    filters += [f'        <button class="chip" data-f="{s}">{STAGE_LABEL[s]}<span class="count">{counts[s]}</span></button>' for s in STAGE_IDS]
    steps = [
        f'      <div class="step"><div class="n">0{i + 1} · {label.upper()}</div><h4>{label}</h4><p>{esc(desc)}</p><span class="badge st-{sid}">{counts[sid]} now</span></div>'
        for i, (sid, label, desc) in enumerate(STAGES)
    ]
    cards, bodies, data = [], [], {"stages": [{"id": s, "label": l, "desc": d} for s, l, d in STAGES], "experiments": []}
    for i, e in enumerate(exps):
        seed = 11 + 12 * i
        cards.append(card_html(e, seed))
        bodies.append(f'<template id="body-{e["slug"]}">{video_html(e.get("video"))}{body_html(e)}</template>')
        inv = e.get("involve") or {}
        data["experiments"].append({
            "slug": e["slug"], "title": e["title"], "stage": e["stage"], "summary": e["summary"],
            "byline": byline(e), "links": e.get("links") or [],
            "charts": [chart_data(c) for c in e.get("charts") or []],
            "involve": {"title": inv.get("title", ""), "text": inv.get("text", "")},
        })

    page = TEMPLATE.read_text(encoding="utf-8")
    version = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
    for key, val in {
        "FILTERS": "\n".join(filters), "CARDS": "\n".join(cards), "STEPS": "\n".join(steps),
        "BODIES": "\n".join(bodies), "COUNT": str(len(exps)), "REPO_URL": REPO_URL, "VERSION": version,
        "DATA": json.dumps(data, ensure_ascii=False, default=str).replace("</", "<\\/"),
    }.items():
        page = page.replace("{{" + key + "}}", val)

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    shutil.copytree(ASSETS, DIST / "assets")
    (DIST / "index.html").write_text(page, encoding="utf-8")

    # A small share page per experiment, so links unfurl with the right title.
    for e in exps:
        d = DIST / "e" / e["slug"]
        d.mkdir(parents=True)
        (d / "index.html").write_text(
            f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/>
<title>{esc(e['title'])} — OHS Labs</title>
<meta property="og:title" content="{esc(e['title'])} — OHS Labs"/>
<meta property="og:description" content="{esc(e['summary'])}"/>
<meta name="description" content="{esc(e['summary'])}"/>
<meta http-equiv="refresh" content="0; url=../../#/{e['slug']}"/>
<link rel="canonical" href="../../#/{e['slug']}"/></head>
<body><a href="../../#/{e['slug']}">{esc(e['title'])}</a></body></html>
""", encoding="utf-8")
    print(f"Wrote {DIST / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
