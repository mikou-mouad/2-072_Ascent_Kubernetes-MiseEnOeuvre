"""API de la billetterie FestiPass.

Volontairement simple : bibliothèque standard + psycopg, logs JSON sur stdout.
Chaque billet est signé (PBKDF2) : c'est ce calcul qui consomme du CPU au rush.
"""
import hashlib
import json
import os
import signal
import socket
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import psycopg

VERSION = os.environ.get("APP_VERSION", "1.0")
FESTIVAL = os.environ.get("FESTIVAL", "Festival des Embruns")
PORT = int(os.environ.get("PORT", "8080"))
# Au-delà de ce nombre de billets dans une commande, elle est refusée (anti-revente).
PASS_MAX = int(os.environ.get("PASS_MAX", "4"))
CLE_SIGNATURE = os.environ.get("CLE_SIGNATURE", "cle-de-dev")
# Coût de la signature d'un billet : plus c'est haut, plus c'est sûr… et gourmand en CPU.
ITERATIONS = int(os.environ.get("SIGNATURE_ITERATIONS", "100000"))

PASSES = [
    {"id": "vendredi", "nom": "Pass vendredi", "prix": 49.0},
    {"id": "samedi", "nom": "Pass samedi", "prix": 59.0},
    {"id": "dimanche", "nom": "Pass dimanche", "prix": 49.0},
    {"id": "3-jours", "nom": "Pass 3 jours", "prix": 129.0},
]
IDS_PASSES = {p["id"] for p in PASSES}

SCHEMA = """
CREATE TABLE IF NOT EXISTS billets (
    code       TEXT PRIMARY KEY,
    nom        TEXT NOT NULL,
    pass       TEXT NOT NULL,
    signature  TEXT NOT NULL,
    vendu_le   TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""


def log(niveau, evenement, **champs):
    ligne = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "niveau": niveau,
        "evenement": evenement,
        "pod": socket.gethostname(),
        **champs,
    }
    print(json.dumps(ligne, ensure_ascii=False), flush=True)


def connexion():
    return psycopg.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ.get("DB_NAME", "festipass"),
        user=os.environ.get("DB_USER", "festipass"),
        password=os.environ.get("DB_PASSWORD", ""),
        connect_timeout=3,
    )


def assurer_schema():
    # Pas de cache : si PostgreSQL repart d'un volume vide, la table est recréée.
    with connexion() as cx:
        cx.execute(SCHEMA)


def signer(code):
    return hashlib.pbkdf2_hmac("sha256", code.encode(), CLE_SIGNATURE.encode(), ITERATIONS).hex()[:16]


class Handler(BaseHTTPRequestHandler):
    server_version = "festipass-back"

    def log_message(self, *args):  # les logs d'accès passent par log()
        pass

    def repondre(self, code, corps):
        donnees = json.dumps(corps, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(donnees)))
        self.end_headers()
        self.wfile.write(donnees)

    def do_GET(self):
        route = self.path.split("?")[0]
        if route == "/healthz":
            return self.repondre(200, {"statut": "ok"})
        if route == "/readyz":
            try:
                assurer_schema()
                return self.repondre(200, {"statut": "pret"})
            except Exception as e:  # noqa: BLE001
                log("WARN", "base_indisponible", erreur=str(e))
                return self.repondre(503, {"statut": "base indisponible"})
        if route == "/api/version":
            return self.repondre(200, {
                "version": VERSION, "festival": FESTIVAL, "pass_max": PASS_MAX, "pod": socket.gethostname(),
            })
        if route == "/api/passes":
            return self.repondre(200, PASSES)
        if route in ("/api/billets", "/api/stats"):
            try:
                assurer_schema()
                with connexion() as cx:
                    if route == "/api/stats":
                        lignes = cx.execute("SELECT pass, count(*) FROM billets GROUP BY pass").fetchall()
                        return self.repondre(200, {l[0]: l[1] for l in lignes})
                    lignes = cx.execute(
                        "SELECT code, nom, pass, signature, vendu_le FROM billets ORDER BY vendu_le DESC LIMIT 20"
                    ).fetchall()
            except Exception as e:  # noqa: BLE001
                log("ERROR", "lecture_billets_impossible", erreur=str(e))
                return self.repondre(503, {"erreur": "base indisponible"})
            return self.repondre(200, [
                {"code": l[0], "nom": l[1], "pass": l[2], "signature": l[3], "vendu_le": l[4].isoformat()}
                for l in lignes
            ])
        return self.repondre(404, {"erreur": "introuvable"})

    def do_POST(self):
        if self.path.split("?")[0] != "/api/billets":
            return self.repondre(404, {"erreur": "introuvable"})
        try:
            longueur = int(self.headers.get("Content-Length", "0"))
            donnees = json.loads(self.rfile.read(longueur) or b"{}")
            nom = str(donnees["nom"]).strip()
            id_pass = str(donnees["pass"])
            quantite = int(donnees.get("quantite", 1))
            if not nom or id_pass not in IDS_PASSES or quantite < 1:
                raise ValueError
        except (KeyError, ValueError, json.JSONDecodeError):
            return self.repondre(400, {"erreur": "commande invalide (nom, pass, quantite)"})

        if quantite > PASS_MAX:
            log("WARN", "commande_refusee", nom=nom, pass_=id_pass, quantite=quantite,
                raison=f"plus de {PASS_MAX} billets")
            return self.repondre(409, {"erreur": f"{PASS_MAX} billets maximum par commande"})

        billets = []
        for _ in range(quantite):
            code = uuid.uuid4().hex[:10].upper()
            billets.append((code, nom, id_pass, signer(code)))

        try:
            assurer_schema()
            with connexion() as cx:
                with cx.cursor() as cur:
                    cur.executemany(
                        "INSERT INTO billets (code, nom, pass, signature) VALUES (%s, %s, %s, %s)", billets
                    )
        except Exception as e:  # noqa: BLE001
            log("ERROR", "vente_impossible", nom=nom, pass_=id_pass, erreur=str(e))
            return self.repondre(503, {"erreur": "base indisponible"})

        codes = [b[0] for b in billets]
        log("INFO", "billets_vendus", nom=nom, pass_=id_pass, quantite=quantite, codes=codes)
        return self.repondre(201, {"codes": codes})


def main():
    serveur = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)

    def arreter(signum, _frame):
        log("INFO", "arret", signal=signum)
        threading.Thread(target=serveur.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, arreter)
    signal.signal(signal.SIGINT, arreter)
    log("INFO", "demarrage", version=VERSION, port=PORT, festival=FESTIVAL, pass_max=PASS_MAX)
    serveur.serve_forever()


if __name__ == "__main__":
    main()
