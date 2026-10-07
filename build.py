#!/usr/bin/env python3
"""Génère les pages HTML importables dans Bring à partir de fichiers listes/*.txt.

Format d'un fichier liste (listes/2026-S42.txt) :
    # Titre de la liste            (1re ligne commençant par # = titre)
    ## Fruits & légumes             (sections = rayons, facultatif)
    Pommes de terre | 2,5 kg        (article | quantité)
    Carottes | 1 kg
    Pain                            (quantité facultative)

Usage : python3 build.py   → régénère listes/*.html + index.html
"""
import html, json, pathlib, re, urllib.parse

ROOT = pathlib.Path(__file__).parent
BASE_URL = "https://alexwattel1.github.io/courses-bring/"
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
<style>body{{font-family:-apple-system,system-ui,sans-serif;max-width:640px;margin:0 auto;padding:16px;line-height:1.5}}
.btn{{display:block;background:#2a9d8f;color:#fff;text-align:center;padding:14px;border-radius:10px;font-size:18px;text-decoration:none;margin:16px 0}}
h2{{font-size:17px;margin-top:22px;border-bottom:1px solid #ddd}} ul{{padding-left:20px}} small{{color:#666}}</style></head>
<body itemscope itemtype="https://schema.org/Recipe"><h1 itemprop="name">{html.escape(title)}</h1>
<a class="btn" href="{link}">➕ Importer dans Bring</a>
<small>{len(ingredients)} articles · ouvre l'app Bring, puis décochez ce que vous avez déjà.</small>
{''.join(body)}
<p><a href="../">← toutes les listes</a></p></body></html>"""
    (ROOT / "listes" / (path.stem + ".html")).write_text(out, encoding="utf-8")
    return path.stem, title, len(ingredients)

def main():
    rows = sorted((render(p) for p in (ROOT / "listes").glob("*.txt")), reverse=True)
    items = "".join(f"<li><a href='listes/{s}.html'>{html.escape(t)}</a> <small>({n} articles)</small></li>" for s, t, n in rows)
    (ROOT / "index.html").write_text(f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Listes de courses</title>
<style>body{{font-family:-apple-system,system-ui,sans-serif;max-width:640px;margin:0 auto;padding:16px;line-height:1.7}}</style></head>
<body><h1>Listes de courses</h1><ul>{items}</ul></body></html>""", encoding="utf-8")
    print(f"{len(rows)} liste(s) générée(s)")

if __name__ == "__main__":
    main()
