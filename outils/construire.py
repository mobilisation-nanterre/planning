"""Fabrique la copie publique (index.html) du planning des salles.

Usage : python3 outils/construire.py DOSSIER_DONNEES
DOSSIER_DONNEES contient salles/*.json et reservations/*.json, tels que les
écrit l'export de la base de la page Claude (un fichier JSON par document).
Écrit index.html à la racine du dépôt. Les identifiants des auteurs ne sont pas publiés.
"""
import json, sys, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = pathlib.Path(sys.argv[1])
PUBLIC_FIELDS = {"date", "debut", "fin", "salle", "salleId", "batiment", "intitule", "demandeur", "statut", "remarques",
                 "nom", "etage", "capacite", "usage"}

def load(coll):
    out = []
    for f in sorted((SRC / coll).glob("*.json")):
        raw = json.loads(f.read_text(encoding="utf-8"))
        data = raw.get("data", raw) if isinstance(raw, dict) else {}
        doc_id = raw.get("id", f.stem) if isinstance(raw, dict) and "data" in raw else f.stem
        out.append({"id": doc_id, "data": {k: v for k, v in data.items() if k in PUBLIC_FIELDS}})
    return out

snap = {"genere": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "salles": load("salles"), "reservations": load("reservations")}
payload = json.dumps(snap, ensure_ascii=False).replace("</", "<\\/")
page = (ROOT / "outils" / "modele.html").read_text(encoding="utf-8")
html = ("<!doctype html><html lang=\"fr\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">"
        "<meta name=\"robots\" content=\"noindex\">"
        "<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}"
        "body{margin:0;font:14px system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>"
        "</head><body>"
        f"<script>window.__SNAPSHOT={payload};</script>\n{page}\n</body></html>\n")
(ROOT / "index.html").write_text(html, encoding="utf-8")
print(f"index.html : {len(snap['salles'])} salles, {len(snap['reservations'])} réservations")
