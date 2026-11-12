"""Fabrique la copie publique (index.html) du planning, par mise à jour incrémentale.

Usage :
  python3 -I outils/construire.py --depuis-quand
      affiche l'horodatage à partir duquel relire les changements (dernière mise à jour moins 15 minutes).
  python3 -I outils/construire.py DOSSIER
      repart de la version publiée (index.html), puis applique les fichiers présents dans DOSSIER :
        reservations.jsonl  réservations créées ou modifiées
        salles.jsonl        salles créées ou modifiées
        suppressions.jsonl  réservations ou salles supprimées
      Chaque fichier contient des lignes JSON {"id": ..., "data": {...}} recopiées telles quelles depuis la
      lecture de la base. Un fichier absent ou vide signifie « aucun changement ».
Écrit index.html à la racine du dépôt. Les identifiants des auteurs ne sont pas publiés.
"""
import json, sys, pathlib, datetime, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
PUBLIC_FIELDS = {"date", "debut", "fin", "salle", "salleId", "batiment", "intitule", "demandeur", "statut", "remarques",
                 "nom", "etage", "capacite", "usage", "categorie"}

def snapshot():
    if not INDEX.exists():
        return {"salles": [], "reservations": []}
    m = re.search(r"window\.__SNAPSHOT=(.*?);</script>", INDEX.read_text(encoding="utf-8"), re.S)
    return json.loads(m.group(1).replace("<\\/", "</")) if m else {"salles": [], "reservations": []}

if sys.argv[1:] == ["--depuis-quand"]:
    g = snapshot().get("genere")
    t = datetime.datetime.fromisoformat(g) if g else datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    print((t - datetime.timedelta(minutes=15)).astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"))
    sys.exit(0)

SRC = pathlib.Path(sys.argv[1])

def clean(doc_id, data):
    return {"id": str(doc_id), "data": {k: v for k, v in (data or {}).items() if k in PUBLIC_FIELDS}}

def lines(name):
    """Lit un fichier de lignes JSON. Tolère un document coupé sur plusieurs lignes (par exemple quand un
    retour à la ligne d'une remarque a été recopié comme un vrai saut de ligne)."""
    f, out = SRC / name, []
    if not f.exists():
        return out
    buf, start = "", 0
    for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        if not buf:
            if not line.strip().startswith("{"):
                continue
            buf, start = line.strip(), n
        else:
            buf += "\n" + line
        try:
            o = json.loads(buf, strict=False)
        except json.JSONDecodeError:
            if n - start > 50:
                sys.exit(f"{name}, à partir de la ligne {start} : JSON invalide — index.html n'est pas modifié.")
            continue
        buf = ""
        if isinstance(o, dict) and "id" in o and isinstance(o.get("data"), dict):
            out.append(o)
    if buf:
        sys.exit(f"{name}, à partir de la ligne {start} : JSON incomplet — index.html n'est pas modifié.")
    return out

snap = snapshot()
salles = {s["id"]: s for s in snap.get("salles", [])}
resas = {r["id"]: r for r in snap.get("reservations", [])}
nr = ns = nd = 0
for o in lines("salles.jsonl"):
    salles[str(o["id"])] = clean(o["id"], o["data"]); ns += 1
for o in lines("reservations.jsonl"):
    resas[str(o["id"])] = clean(o["id"], o["data"]); nr += 1
for o in lines("suppressions.jsonl"):
    kind, i = o["data"].get("type"), str(o["id"])
    if kind == "salle" and salles.pop(i, None): nd += 1
    elif kind != "salle" and resas.pop(i, None): nd += 1
if not salles:
    sys.exit("Aucune salle : index.html n'est pas modifié.")

out = {"genere": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
       "salles": list(salles.values()), "reservations": list(resas.values())}
payload = json.dumps(out, ensure_ascii=False).replace("</", "<\\/")
page = (ROOT / "outils" / "modele.html").read_text(encoding="utf-8")
html = ("<!doctype html><html lang=\"fr\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">"
        "<meta name=\"robots\" content=\"noindex\">"
        "<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}"
        "body{margin:0;font:14px system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>"
        "</head><body>"
        f"<script>window.__SNAPSHOT={payload};</script>\n{page}\n</body></html>\n")
INDEX.write_text(html, encoding="utf-8")
print(f"index.html : {len(salles)} salles, {len(resas)} réservations "
      f"({nr} réservation(s) et {ns} salle(s) lues, {nd} suppression(s) appliquée(s))")
