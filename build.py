#!/usr/bin/env python3
"""Site « Cuisine maison » : menus semaine par semaine, fiches recettes et listes importables dans Bring.

Sources :
  menus/AAAA-Sxx.json   → une semaine (recettes choisies, coût, liste associée)
  listes/AAAA-Sxx.txt   → liste de courses (« # Titre », « ## Rayon », « Article | quantité »)
  RECETTES_DIR/*.md     → fiches recettes du vault (frontmatter + ## Ingrédients / ## Étapes / ## Notes)

Usage : python3 build.py
"""
import html, json, pathlib, re, urllib.parse

ROOT = pathlib.Path(__file__).parent
RECETTES_DIR = pathlib.Path.home() / "dev/Second Brain AWA/RESSOURCES/Cuisine/Recettes"
BASE_URL = "https://wattel-maison.github.io/courses-bring/"
BRING = "https://api.getbring.com/rest/bringrecipes/deeplink?url={url}&source=web&baseQuantity={q}&requestedQuantity={q}"

FAVICON = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ctext y='26' font-size='26'%3E%F0%9F%8D%B3%3C/text%3E%3C/svg%3E"

CSS = """
:root{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--muted:#86868b;--body:#4b4b50;--line:#e8e8ed;--accent:#0071e3;--accent-soft:#eaf3fe;--hg:linear-gradient(120deg,#0090ff,#7a5cff);color-scheme:light}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.6 -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",Roboto,"Helvetica Neue",sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:900px;margin:0 auto;padding:0 16px}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
header{padding:14px 0;background:rgba(255,255,255,.85);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);position:sticky;top:0;z-index:10;border-bottom:1px solid var(--line)}
header .wrap{display:flex;align-items:center;gap:14px}
.brand{font-size:24px;font-weight:700;letter-spacing:-.02em;color:var(--ink);display:flex;align-items:center;gap:9px}.brand:hover{text-decoration:none}
.ai{background:var(--hg);-webkit-background-clip:text;background-clip:text;color:transparent}
.spacer{flex:1}
nav.menu{display:flex;gap:18px;font-size:14px}nav.menu a{color:var(--body);white-space:nowrap}nav.menu a.on{color:var(--ink);font-weight:600}
main{padding:36px 0 72px}
h1{font-size:clamp(34px,7vw,56px);line-height:1.05;font-weight:800;letter-spacing:-.04em;margin:0 0 10px;text-wrap:balance}
h1 em{font-style:normal;background:var(--hg);-webkit-background-clip:text;background-clip:text;color:transparent;padding-bottom:.05em}
.lede{font-size:18px;color:var(--body);max-width:38em;margin:0 0 30px}
h2{font-size:clamp(24px,4vw,32px);line-height:1.1;font-weight:800;letter-spacing:-.03em;margin:0 0 6px}
h3{font-size:19px;font-weight:700;margin:26px 0 8px;letter-spacing:-.01em}
.card{background:var(--card);border-radius:16px;padding:22px 24px;box-shadow:0 1px 3px rgba(0,0,0,.05);margin:0 0 18px}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:11px 22px;border-radius:980px;font-weight:500;font-size:16px;min-height:44px;transition:filter .15s}
.btn:hover{filter:brightness(1.07);text-decoration:none}
.btn-primary{background:linear-gradient(135deg,#0090ff,#7a5cff);color:#fff}
.btn-ghost{background:#e8e8ed;color:var(--ink)}
.btn-sm{padding:7px 14px;font-size:14px;min-height:34px}
.pill{font-size:11px;font-weight:700;border-radius:980px;padding:3px 10px;letter-spacing:.03em;background:var(--accent-soft);color:var(--accent);white-space:nowrap}
.muted{color:var(--muted);font-size:14px}
.meta{color:var(--body);font-size:15px;margin:0 0 18px}
table{width:100%;border-collapse:collapse;font-size:16px}
th{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);text-align:left;padding:0 8px 8px;font-weight:600}
td{padding:10px 8px;border-top:1px solid var(--line);vertical-align:middle}
td.day{white-space:nowrap;color:var(--body);font-size:14px;width:1%}
td.cost{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums;width:1%}
td.chk{width:1%;padding-right:0}
input[type=checkbox]{width:22px;height:22px;accent-color:var(--accent);cursor:pointer}
tr.off td:not(.chk){opacity:.4;text-decoration:line-through}
tr.off td.cost{text-decoration:none}
.total{display:flex;align-items:baseline;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-top:14px;padding-top:14px;border-top:2px solid var(--ink)}
.total b{font-size:26px;letter-spacing:-.02em}
.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}
.weekhead{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:12px}
.weekhead .dates{color:var(--body)}
ul.ing{padding-left:22px;font-size:18px}ul.ing li{margin:5px 0}
ol.steps{padding-left:24px;font-size:18px}ol.steps li{margin:14px 0}
ul.notes{padding-left:22px;color:var(--body)}
.rayon h3{margin-top:18px}
.recipes{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}
.recipes a{display:block;background:var(--card);border-radius:14px;padding:16px 18px;box-shadow:0 1px 3px rgba(0,0,0,.05);color:var(--ink);font-weight:600;line-height:1.3}
.recipes a small{display:block;color:var(--muted);font-weight:400;margin-top:4px;font-size:13px}
.recipes a:hover{text-decoration:none;box-shadow:0 6px 18px rgba(0,0,0,.08)}
footer{color:var(--muted);font-size:13px;text-align:center;padding:30px 0}
@media (max-width:600px){td,th{padding-left:4px;padding-right:4px}.btn{width:100%}}
"""

def page(title, body, depth=0, active=""):
    p = "../" * depth
    nav = "".join(f'<a href="{p}{h}" class="{"on" if active == k else ""}">{t}</a>' for k, h, t in
                  [("menus", "index.html", "Menus"), ("recettes", "recettes.html", "Recettes"), ("listes", "listes.html", "Listes")])
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} — Cuisine maison</title>
<meta name="theme-color" content="#f5f5f7"><link rel="icon" href="{FAVICON}"><style>{CSS}</style></head>
<body><header><div class="wrap"><a class="brand" href="{p}index.html"><span>Cuisine <span class="ai">maison</span></span></a>
<span class="spacer"></span><nav class="menu">{nav}</nav></div></header>
<main><div class="wrap">{body}</div></main>
<footer>Menus, recettes et listes de la famille · généré depuis le second brain</footer></body></html>"""

def slugify(t):
    t = t.lower()
    for a, b in zip("àâäéèêëîïôöùûüç", "aaaeeeeiioouuuc"): t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")

def euro(v):
    return f"{v:.0f} €"

# ---------- listes ----------
def parse_list(path):
    title, sections, cur = path.stem, [], None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line: continue
        if line.startswith("## "): cur = (line[3:].strip(), []); sections.append(cur); continue
        if line.startswith("# "): title = line[2:].strip(); continue
        if cur is None: cur = ("Liste", []); sections.append(cur)
        item, _, qty = (x.strip() for x in line.partition("|"))
        cur[1].append((item, qty))
    return title, sections

def render_list(path):
    title, sections = parse_list(path)
    url = BASE_URL + "listes/" + path.stem + ".html"
    ings = [f"{q} {i}".strip() if q else i for _, items in sections for i, q in items]
    ld = {"@context": "https://schema.org", "@type": "Recipe", "name": title, "author": {"@type": "Person", "name": "Alexandre"},
          "recipeYield": "1", "recipeCategory": "Courses", "recipeIngredient": ings, "recipeInstructions": "Liste de courses de la semaine."}
    link = BRING.format(url=urllib.parse.quote(url, safe=""), q=1)
    body = f'<h1>{html.escape(title)}</h1><p class="meta">{len(ings)} articles · le bouton ouvre Bring avec tout pré-rempli, vous décochez ce que vous avez déjà.</p>' \
           f'<a class="btn btn-primary" href="{link}">Importer dans Bring</a>'
    for sec, items in sections:
        body += f'<div class="rayon"><h3>{html.escape(sec)}</h3><ul class="ing">' + "".join(
            f"<li>{html.escape((q + ' ' + i).strip() if q else i)}</li>" for i, q in items) + "</ul></div>"
    out = page(title, body, 1, "listes").replace("<style>", f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script><style>', 1)
    (ROOT / "listes" / (path.stem + ".html")).write_text(out, encoding="utf-8")
    return path.stem, title, len(ings)

# ---------- recettes ----------
def parse_recipe(path):
    txt = path.read_text(encoding="utf-8"); meta, body = {}, txt
    if txt.startswith("---"):
        _, fm, body = txt.split("---", 2)
        for l in fm.strip().splitlines():
            k, _, v = l.partition(":"); meta[k.strip()] = v.strip()
    title, sections, cur = path.stem, {}, None
    for raw in body.splitlines():
        line = raw.rstrip()
        if line.startswith("# "): title = line[2:].strip(); continue
        if line.startswith("## "): cur = line[3:].strip().lower(); sections[cur] = []; continue
        if cur and line.strip(): sections[cur].append(re.sub(r"^(\d+\.|-|\*)\s*", "", line.strip()))
    return title, meta, sections

def render_recipe(path):
    title, meta, sec = parse_recipe(path)
    slug = slugify(title); url = BASE_URL + "recettes/" + slug + ".html"
    ings = []
    for l in sec.get("ingrédients", []):
        q, _, i = (x.strip() for x in l.partition("|")); ings.append(f"{q} {i}".strip() if i else q)
    steps, notes, parts = sec.get("étapes", []), sec.get("notes", []), meta.get("parts", "6")
    ld = {"@context": "https://schema.org", "@type": "Recipe", "name": title, "author": {"@type": "Person", "name": "Alexandre"},
          "recipeYield": parts, "recipeIngredient": ings, "recipeInstructions": [{"@type": "HowToStep", "text": s} for s in steps]}
    link = BRING.format(url=urllib.parse.quote(url, safe=""), q=parts)
    src = " · ".join(x for x in [meta.get("titre_livre"), f"p. {meta['page']}" if meta.get("page") else None, f"{parts} parts", meta.get("temps")] if x)
    body = f'<h1>{html.escape(title)}</h1><p class="meta">{html.escape(src)}</p><a class="btn btn-primary" href="{link}">Ingrédients dans Bring</a>' \
           f'<h3>Ingrédients</h3><ul class="ing">{"".join(f"<li>{html.escape(i)}</li>" for i in ings)}</ul>' \
           f'<h3>Étapes</h3><ol class="steps">{"".join(f"<li>{html.escape(s)}</li>" for s in steps)}</ol>'
    if notes: body += f'<h3>Notes</h3><ul class="notes">{"".join(f"<li>{html.escape(n)}</li>" for n in notes)}</ul>'
    out = page(title, body, 1, "recettes").replace("<style>", f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script><style>', 1)
    (ROOT / "recettes").mkdir(exist_ok=True)
    (ROOT / "recettes" / (slug + ".html")).write_text(out, encoding="utf-8")
    return slug, title, meta.get("titre_livre", ""), link

# ---------- menus ----------
def render_week(m, recipes):
    by_slug = {s: (t, b, l) for s, t, b, l in recipes}
    rows, data = "", []
    for i, r in enumerate(m["recettes"]):
        slug = r.get("slug"); bring = ""
        name = f'<a href="recettes/{slug}.html">{html.escape(r["titre"])}</a>' if slug and slug in by_slug else html.escape(r["titre"])
        if slug and slug in by_slug: bring = f'<a class="pill" href="{by_slug[slug][2]}">Bring</a>'
        ref = html.escape(f'{r.get("livre","")} p.{r["page"]}' if r.get("page") else r.get("livre", ""))
        rows += f'<tr data-i="{i}" data-cost="{r["cout"]}"><td class="chk"><input type="checkbox" checked aria-label="prendre {html.escape(r["titre"])}"></td>' \
                f'<td class="day">{html.escape(r["jour"])}<br><span class="muted">{html.escape(r["repas"])}</span></td>' \
                f'<td>{name}<br><span class="muted">{ref}</span> {bring}</td><td class="cost">{euro(r["cout"])}</td></tr>'
    base = m.get("basiques", 0)
    actions = f'<a class="btn btn-primary" href="listes/{m["liste"]}.html">Liste de courses → Bring</a>' if m.get("liste") else ""
    return f"""<section class="card week" data-week="{m['semaine']}" data-base="{base}">
<div class="weekhead"><h2>{html.escape(m['semaine'])}</h2><span class="dates">{html.escape(m['dates'])}</span></div>
{('<p class="meta">' + html.escape(m['note']) + '</p>') if m.get('note') else ''}
<table><thead><tr><th></th><th>Jour</th><th>Recette</th><th style="text-align:right">Coût</th></tr></thead><tbody>{rows}</tbody>
<tfoot><tr><td></td><td class="day">Base</td><td><span class="muted">Petit-déj, goûters, fruits, laitages, pain</span></td><td class="cost">{euro(base)}</td></tr></tfoot></table>
<div class="total"><span class="muted">Coût estimé des recettes cochées, ± 15 %</span><b class="sum"></b></div>
<div class="actions">{actions}</div></section>"""

JS = """
document.querySelectorAll('.week').forEach(w=>{
  const key='menu-'+w.dataset.week, base=+w.dataset.base;
  let st={}; try{st=JSON.parse(localStorage.getItem(key)||'{}')}catch(e){}
  const rows=[...w.querySelectorAll('tbody tr')];
  const sum=()=>{let t=base;rows.forEach(r=>{const on=r.querySelector('input').checked;r.classList.toggle('off',!on);if(on)t+=+r.dataset.cost});w.querySelector('.sum').textContent=Math.round(t)+' €'};
  rows.forEach(r=>{const c=r.querySelector('input');if(st[r.dataset.i]===false)c.checked=false;
    c.addEventListener('change',()=>{st[r.dataset.i]=c.checked;try{localStorage.setItem(key,JSON.stringify(st))}catch(e){};sum()})});
  sum();
});"""

def main():
    (ROOT / "listes").mkdir(exist_ok=True)
    lists = sorted((render_list(p) for p in (ROOT / "listes").glob("*.txt")), reverse=True)
    recipes = sorted(render_recipe(p) for p in RECETTES_DIR.glob("*.md")) if RECETTES_DIR.exists() else []
    menus = sorted((json.loads(p.read_text(encoding="utf-8")) for p in (ROOT / "menus").glob("*.json")), key=lambda m: m["semaine"], reverse=True)

    home = '<h1>Les menus de la <em>semaine</em></h1><p class="lede">Une ligne par recette. Décochez ce qu\'on ne fera pas : le coût se recalcule. Chaque recette a sa fiche et son bouton Bring.</p>'
    home += "".join(render_week(m, recipes) for m in menus) or '<div class="card">Aucun menu pour l\'instant.</div>'
    home += f"<script>{JS}</script>"
    (ROOT / "index.html").write_text(page("Menus", home, 0, "menus"), encoding="utf-8")

    rec = '<h1>Les <em>recettes</em></h1><p class="lede">Les fiches numérisées depuis nos livres, quantités pour 6 parts sauf mention.</p><div class="recipes">' + \
          "".join(f'<a href="recettes/{s}.html">{html.escape(t)}<small>{html.escape(b)}</small></a>' for s, t, b, _ in recipes) + "</div>"
    (ROOT / "recettes.html").write_text(page("Recettes", rec, 0, "recettes"), encoding="utf-8")

    lst = '<h1>Les <em>listes</em> de courses</h1><p class="lede">Une liste par semaine, importable dans Bring en un bouton.</p><div class="recipes">' + \
          "".join(f'<a href="listes/{s}.html">{html.escape(t)}<small>{n} articles</small></a>' for s, t, n in lists) + "</div>"
    (ROOT / "listes.html").write_text(page("Listes", lst, 0, "listes"), encoding="utf-8")
    print(f"{len(menus)} menu(s), {len(lists)} liste(s), {len(recipes)} recette(s)")

if __name__ == "__main__":
    main()
