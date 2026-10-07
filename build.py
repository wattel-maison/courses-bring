#!/usr/bin/env python3
"""Génère les pages HTML importables dans Bring à partir de fichiers listes/*.txt.

Format d'un fichier liste (listes/2026-S42.txt) :
    # Titre de la liste            (1re ligne commençant par # = titre)
    ## Fruits & légumes             (sections = rayons, facultatif)
    Pommes de terre | 2,5 kg        (article | quantité)
    Carottes | 1 kg
    Pain                            (quantité facultative)

Les fiches recettes sont lues dans le vault (RECETTES_DIR), format :
    ---
    livre: L6 · titre_livre: Whoogy's — Daylycieux · page: 178 · parts: 6 · temps: 2 h 30
    ---
    # Joues de porc au cidre
    ## Ingrédients
    - 1,2 kg | joues de porc          (quantité | article — ou juste l'article)
    ## Étapes
    1. ...
    ## Notes
    ...

Usage : python3 build.py   → régénère listes/*.html, recettes/*.html et index.html
"""
import html, json, pathlib, re, urllib.parse

ROOT = pathlib.Path(__file__).parent
RECETTES_DIR = pathlib.Path.home() / "dev/Second Brain AWA/RESSOURCES/Cuisine/Recettes"
CSS = """body{font-family:-apple-system,system-ui,sans-serif;max-width:680px;margin:0 auto;padding:16px;line-height:1.55;font-size:18px}
.btn{display:block;background:#2a9d8f;color:#fff;text-align:center;padding:14px;border-radius:10px;font-size:18px;text-decoration:none;margin:16px 0}
h1{line-height:1.2} h2{font-size:19px;margin-top:26px;border-bottom:1px solid #ddd} ul,ol{padding-left:22px} li{margin:6px 0} small{color:#666}
.meta{color:#666;font-size:15px} ol li{margin:12px 0}"""
BASE_URL = "https://hailp.tech/courses-bring/"
DEEPLINK = "https://api.getbring.com/rest/bringrecipes/deeplink?url={url}&source=web&baseQuantity=1&requestedQuantity=1"

def parse(path):
    title, sections, cur = path.stem, [], None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("## "):
            cur = (line[3:].strip(), []); sections.append(cur); continue
        if line.startswith("# "):
            title = line[2:].strip(); continue
        if cur is None:
            cur = ("Liste", []); sections.append(cur)
        item, _, qty = (p.strip() for p in line.partition("|"))
        cur[1].append((item, qty))
    return title, sections

def render(path):
    title, sections = parse(path)
    page_url = BASE_URL + "listes/" + path.stem + ".html"
    ingredients = [f"{q} {i}".strip() if q else i for _, items in sections for i, q in items]
    ld = {
        "@context": "https://schema.org", "@type": "Recipe",
        "name": title, "author": {"@type": "Person", "name": "Alexandre"},
        "recipeYield": "1", "recipeCategory": "Courses",
        "recipeIngredient": ingredients,
        "recipeInstructions": "Liste de courses de la semaine.",
    }
    link = DEEPLINK.format(url=urllib.parse.quote(page_url, safe=""))
    body = []
    for sec, items in sections:
        body.append(f"<h2>{html.escape(sec)}</h2><ul>")
        body += [f"<li itemprop='recipeIngredient'>{html.escape((q + ' ' + i).strip() if q else i)}</li>" for i, q in items]
        body.append("</ul>")
    out = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<style>{CSS}</style></head>
<body itemscope itemtype="https://schema.org/Recipe"><h1 itemprop="name">{html.escape(title)}</h1>
<a class="btn" href="{link}">➕ Importer dans Bring</a>
<small>{len(ingredients)} articles · ouvre l'app Bring, puis décochez ce que vous avez déjà.</small>
{''.join(body)}
<p><a href="../">← toutes les listes</a></p></body></html>"""
    (ROOT / "listes" / (path.stem + ".html")).write_text(out, encoding="utf-8")
    return path.stem, title, len(ingredients)

def slugify(t):
    t = t.lower()
    for a, b in zip("àâäéèêëîïôöùûüç", "aaaeeeeiioouuuc"): t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")

def parse_recipe(path):
    txt = path.read_text(encoding="utf-8")
    meta, body = {}, txt
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
    slug = slugify(title)
    page_url = BASE_URL + "recettes/" + slug + ".html"
    ings = []
    for l in sec.get("ingrédients", []):
        q, _, i = (x.strip() for x in l.partition("|"))
        ings.append(f"{q} {i}".strip() if i else q)
    steps = sec.get("étapes", [])
    parts = meta.get("parts", "6")
    ld = {"@context": "https://schema.org", "@type": "Recipe", "name": title,
          "author": {"@type": "Person", "name": "Alexandre"}, "recipeYield": parts,
          "recipeIngredient": ings, "recipeInstructions": [{"@type": "HowToStep", "text": st} for st in steps]}
    if meta.get("temps"): ld["description"] = "Temps : " + meta["temps"]
    link = f"https://api.getbring.com/rest/bringrecipes/deeplink?url={urllib.parse.quote(page_url, safe='')}&source=web&baseQuantity={parts}&requestedQuantity={parts}"
    src = " · ".join(x for x in [meta.get("titre_livre"), ("p. " + meta["page"]) if meta.get("page") else None, (parts + " parts"), meta.get("temps")] if x)
    notes = sec.get("notes", [])
    out = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script><style>{CSS}</style></head>
<body><h1>{html.escape(title)}</h1><p class="meta">{html.escape(src)}</p>
<a class="btn" href="{link}">➕ Ingrédients dans Bring</a>
<h2>Ingrédients</h2><ul>{''.join(f'<li>{html.escape(i)}</li>' for i in ings)}</ul>
<h2>Étapes</h2><ol>{''.join(f'<li>{html.escape(st)}</li>' for st in steps)}</ol>
{('<h2>Notes</h2><ul>' + ''.join(f'<li>{html.escape(n)}</li>' for n in notes) + '</ul>') if notes else ''}
<p><a href="../">← accueil</a></p></body></html>"""
    (ROOT / "recettes").mkdir(exist_ok=True)
    (ROOT / "recettes" / (slug + ".html")).write_text(out, encoding="utf-8")
    return slug, title, meta.get("titre_livre", "")

def main():
    rows = sorted((render(p) for p in (ROOT / "listes").glob("*.txt")), reverse=True)
    items = "".join(f"<li><a href='listes/{s}.html'>{html.escape(t)}</a> <small>({n} articles)</small></li>" for s, t, n in rows)
    recs = sorted(render_recipe(p) for p in RECETTES_DIR.glob("*.md")) if RECETTES_DIR.exists() else []
    recs_html = "".join(f"<li><a href='recettes/{s}.html'>{html.escape(t)}</a> <small>{html.escape(b)}</small></li>" for s, t, b in recs)
    (ROOT / "index.html").write_text(f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Listes de courses</title>
<style>body{{font-family:-apple-system,system-ui,sans-serif;max-width:640px;margin:0 auto;padding:16px;line-height:1.7}}</style></head>
<body><h1>Listes de courses</h1><ul>{items}</ul><h1>Recettes</h1><ul>{recs_html}</ul></body></html>""", encoding="utf-8")
    print(f"{len(rows)} liste(s), {len(recs)} recette(s) générée(s)")

if __name__ == "__main__":
    main()
